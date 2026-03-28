---
name: authentication
description: Authentication patterns - JWT, sessions, OAuth 2.0/OIDC, passkeys, RBAC, MFA. Token rotation, password hashing, rate limiting.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Authentication Patterns

> Production auth patterns covering tokens, sessions, OAuth, and access control.

## Token-Based (JWT)

### Token Strategy
| Token | Lifetime | Storage | Purpose |
|-------|----------|---------|---------|
| Access token | 15 min | Memory/cookie | API authorization |
| Refresh token | 7 days | httpOnly cookie | Token renewal |
| ID token | 15 min | Memory | User identity (OIDC) |

### JWT Best Practices
```typescript
// Sign with RS256 for asymmetric verification
const token = await new SignJWT({ sub: userId, role })
  .setProtectedHeader({ alg: 'RS256' })
  .setIssuedAt()
  .setExpirationTime('15m')
  .setJti(crypto.randomUUID()) // Unique token ID for revocation
  .sign(privateKey);
```

### Token Rotation
```typescript
async function refreshTokens(refreshToken: string) {
  const payload = await verify(refreshToken);
  // Revoke old refresh token (one-time use)
  await revokeToken(payload.jti);
  // Issue new pair
  const newAccess = await signAccessToken(payload.sub);
  const newRefresh = await signRefreshToken(payload.sub);
  return { accessToken: newAccess, refreshToken: newRefresh };
}
```

---

## Session-Based

### Setup
```typescript
// httpOnly cookie - not accessible via JavaScript
Set-Cookie: session_id=abc123;
  HttpOnly;
  Secure;
  SameSite=Lax;
  Path=/;
  Max-Age=86400
```

### Session Store
- **Redis** for distributed systems (TTL = session lifetime)
- **Database** for audit requirements
- Regenerate session ID on privilege change (login, role change)

---

## OAuth 2.0 / OIDC

### Authorization Code Flow (with PKCE)
```
1. Generate code_verifier (random 43-128 chars)
2. Derive code_challenge = BASE64URL(SHA256(code_verifier))
3. Redirect to /authorize?response_type=code&code_challenge=...&state=RANDOM
4. User authenticates at provider
5. Provider redirects back with ?code=AUTH_CODE&state=RANDOM
6. Verify state matches (CSRF prevention)
7. Exchange code + code_verifier for tokens at /token endpoint
```

### Provider Integration
```typescript
// Generic OAuth callback handler
async function handleCallback(code: string, state: string) {
  verifyState(state, session.oauthState);
  const tokens = await exchangeCode(code, codeVerifier);
  const userInfo = await fetchUserInfo(tokens.access_token);
  const user = await findOrCreateUser(userInfo);
  await createSession(user.id);
}
```

---

## Password Hashing

### Recommended Algorithms
| Algorithm | Config | Use When |
|-----------|--------|----------|
| **Argon2id** | memory=64MB, iterations=3, parallelism=4 | Default choice |
| **bcrypt** | cost ≥ 12 | Legacy systems, wider library support |
| **scrypt** | N=2^17, r=8, p=1 | Alternative to Argon2 |

**Never:** MD5, SHA-1, SHA-256 alone, unsalted hashes

---

## RBAC (Role-Based Access Control)

### Permission Model
```typescript
type Permission = 'read' | 'write' | 'delete' | 'admin';
type Role = {
  name: string;
  permissions: Permission[];
  inherits?: string[]; // Role inheritance
};

// Check authorization
function authorize(user: User, required: Permission): boolean {
  const userPerms = resolvePermissions(user.roles);
  return userPerms.includes(required) || userPerms.includes('admin');
}
```

### Middleware Pattern
```typescript
function requirePermission(...perms: Permission[]) {
  return async (req, res, next) => {
    const user = req.user;
    if (!user || !perms.every(p => authorize(user, p))) {
      return res.status(403).json({ error: 'Forbidden' });
    }
    next();
  };
}

// Usage
app.delete('/api/users/:id', requirePermission('admin', 'delete'), handler);
```

---

## MFA (Multi-Factor Authentication)

### TOTP (Time-Based One-Time Password)
```typescript
// Setup: generate secret, show QR code
const secret = generateTOTPSecret();
const qrUrl = `otpauth://totp/App:${email}?secret=${secret}&issuer=App`;

// Verify: check 6-digit code with 30s window
function verifyTOTP(secret: string, code: string): boolean {
  const expected = generateTOTP(secret, Math.floor(Date.now() / 30000));
  return timingSafeEqual(code, expected);
}
```

### Backup Codes
- Generate 10 single-use codes at MFA setup
- Hash and store them (like passwords)
- Mark as used after consumption

---

## Rate Limiting

### Auth Endpoints
| Endpoint | Limit | Window | Action on Exceed |
|----------|-------|--------|-----------------|
| POST /login | 5 attempts | 15 min | Lock + email alert |
| POST /register | 3 attempts | 1 hour | CAPTCHA |
| POST /forgot-password | 3 attempts | 1 hour | Silent (no error leak) |
| POST /verify-mfa | 5 attempts | 5 min | Session invalidation |

### Implementation
```typescript
// Token bucket with Redis
async function rateLimit(key: string, limit: number, windowSec: number) {
  const current = await redis.incr(key);
  if (current === 1) await redis.expire(key, windowSec);
  if (current > limit) throw new TooManyRequestsError();
}
```

---

## Security Checklist
- [ ] Tokens in httpOnly, Secure, SameSite cookies
- [ ] CSRF protection (state parameter, double-submit cookie)
- [ ] Password hashing with Argon2id or bcrypt (cost ≥ 12)
- [ ] Rate limiting on all auth endpoints
- [ ] Session regeneration on privilege change
- [ ] Refresh token rotation (single-use)
- [ ] Secrets from environment variables only
- [ ] No sensitive data in JWT payload (use opaque tokens if needed)
- [ ] Audit logging for login, logout, password change, MFA events
