---
name: caching-strategies
description: Multi-layer caching patterns - Browser, CDN, Redis, app-level, DB cache. Invalidation strategies, ISR, SWR, thundering herd prevention.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Caching Strategies

> End-to-end caching patterns from browser to database.

## 5-Tier Caching Pyramid

```
Browser Cache (fastest, per-user)
  → CDN / Edge Cache (regional, shared)
    → Reverse Proxy (Nginx, Varnish)
      → Application Cache (Redis, in-memory)
        → Database Cache (query cache, materialized views)
```

---

## Primary Strategies

### Cache-Aside (Lazy Loading)
```typescript
async function getData(key: string) {
  let data = await redis.get(key);
  if (!data) {
    data = await db.query(key);
    await redis.set(key, data, { EX: 3600 });
  }
  return data;
}
```
**Use when:** Read-heavy, tolerance for occasional stale data.

### Write-Through
```typescript
async function saveData(key: string, value: any) {
  await db.save(key, value);
  await redis.set(key, value, { EX: 3600 });
}
```
**Use when:** Consistency matters, write frequency is moderate.

### Write-Behind (Write-Back)
- Write to cache immediately, async flush to DB
- **Risk:** Data loss if cache crashes before flush
- **Use when:** High write throughput, eventual consistency OK

### Read-Through
- Cache fetches from DB automatically on miss
- Simpler code, cache library handles population

### Stale-While-Revalidate (SWR)
```typescript
// Return stale data immediately, refresh in background
Cache-Control: max-age=60, stale-while-revalidate=300
```

---

## HTTP Cache Headers

| Directive | Purpose |
|-----------|---------|
| `Cache-Control: public, max-age=31536000` | Static assets (immutable) |
| `Cache-Control: private, no-cache` | Per-user data, always revalidate |
| `Cache-Control: s-maxage=3600, stale-while-revalidate=86400` | CDN cache with SWR |
| `ETag: "abc123"` | Conditional requests (304 Not Modified) |
| `Vary: Accept-Encoding, Authorization` | Cache variants |

---

## Redis Patterns

### Key Naming Convention
```
{service}:{entity}:{id}:{field}
# e.g., app:user:123:profile
```

### TTL Guidelines
| Data Type | TTL | Reason |
|-----------|-----|--------|
| User sessions | 30min-24h | Security |
| API responses | 5min-1h | Freshness |
| Static config | 24h-7d | Rarely changes |
| Computed results | 1h-24h | Cost of recompute |

### Invalidation Patterns

**Event-Driven:**
```typescript
// On data change, publish invalidation event
await redis.del(`app:user:${userId}:profile`);
await redis.publish('cache:invalidate', JSON.stringify({ key, reason }));
```

**Tag-Based:**
```typescript
// Tag cache entries, invalidate by tag
await redis.sadd('tag:user:123', 'app:user:123:profile', 'app:user:123:orders');
// Invalidate all entries for user 123
const keys = await redis.smembers('tag:user:123');
await redis.del(...keys);
```

**Versioned Keys:**
```typescript
const version = await redis.incr('version:products');
const key = `products:v${version}:list`;
```

---

## Next.js Specific

### ISR (Incremental Static Regeneration)
```typescript
// app/products/[id]/page.tsx
export const revalidate = 3600; // Revalidate every hour

// On-demand revalidation
// app/api/revalidate/route.ts
import { revalidatePath, revalidateTag } from 'next/cache';
export async function POST(req: Request) {
  revalidateTag('products');
  return Response.json({ revalidated: true });
}
```

### fetch() Caching
```typescript
// Cache indefinitely (default in Next.js)
fetch(url, { cache: 'force-cache' });

// Revalidate every 60 seconds
fetch(url, { next: { revalidate: 60 } });

// Never cache
fetch(url, { cache: 'no-store' });

// Tag-based
fetch(url, { next: { tags: ['products'] } });
```

---

## Common Pitfalls

| Pitfall | Solution |
|---------|----------|
| **Cache stampede** | Mutex/lock on cache miss, only one request populates |
| **Thundering herd** | Stagger TTLs with jitter: `TTL + random(0, TTL*0.1)` |
| **Dogpiling** | Background refresh before expiry |
| **Key explosion** | Limit key cardinality, use hash structures |
| **Stale data** | Event-driven invalidation, short TTLs for mutable data |
| **Cold start** | Cache warming on deploy |

## Monitoring Targets
- Hit rate > 90%
- P99 latency < 5ms (Redis)
- Eviction rate stable (not climbing)
