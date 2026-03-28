---
name: realtime-patterns
description: WebSocket, Server-Sent Events, real-time sync patterns. Connection management, reconnection, presence, pub/sub, optimistic updates.
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Real-Time Patterns

> Patterns for WebSocket, SSE, and real-time data synchronization.

## Protocol Selection

| Protocol | Direction | Use When |
|----------|-----------|----------|
| **WebSocket** | Bidirectional | Chat, gaming, collaboration |
| **SSE (Server-Sent Events)** | Server → Client | Notifications, feeds, dashboards |
| **HTTP Polling** | Client → Server | Simple updates, fallback |
| **WebTransport** | Bidirectional (QUIC) | Low-latency, unreliable OK |

---

## WebSocket Patterns

### Connection Management
```typescript
class WSClient {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectDelay = 30000;

  connect(url: string) {
    this.ws = new WebSocket(url);

    this.ws.onopen = () => {
      this.reconnectAttempts = 0;
      this.authenticate();
    };

    this.ws.onclose = (event) => {
      if (!event.wasClean) this.reconnect(url);
    };

    this.ws.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      this.handleMessage(msg);
    };
  }

  private reconnect(url: string) {
    // Exponential backoff with jitter
    const delay = Math.min(
      1000 * Math.pow(2, this.reconnectAttempts) + Math.random() * 1000,
      this.maxReconnectDelay
    );
    this.reconnectAttempts++;
    setTimeout(() => this.connect(url), delay);
  }
}
```

### Message Protocol
```typescript
type WSMessage = {
  type: string;        // "chat:message", "presence:update", "sync:state"
  payload: unknown;
  id: string;          // For deduplication
  timestamp: number;
};

// Namespace messages with colon notation
// Enables routing to specific handlers
const handlers: Record<string, (payload: any) => void> = {
  'chat:message': handleChatMessage,
  'presence:update': handlePresence,
  'sync:state': handleStateSync,
};
```

### Server-Side (Node.js)
```typescript
import { WebSocketServer } from 'ws';

const wss = new WebSocketServer({ port: 8080 });
const rooms = new Map<string, Set<WebSocket>>();

wss.on('connection', (ws, req) => {
  const userId = authenticate(req);

  ws.on('message', (data) => {
    const msg = JSON.parse(data.toString());
    switch (msg.type) {
      case 'room:join':
        joinRoom(msg.payload.roomId, ws);
        break;
      case 'room:message':
        broadcastToRoom(msg.payload.roomId, msg, ws);
        break;
    }
  });

  // Heartbeat to detect dead connections
  ws.isAlive = true;
  ws.on('pong', () => { ws.isAlive = true; });
});

// Ping every 30 seconds, terminate dead connections
setInterval(() => {
  wss.clients.forEach((ws) => {
    if (!ws.isAlive) return ws.terminate();
    ws.isAlive = false;
    ws.ping();
  });
}, 30000);
```

---

## Server-Sent Events (SSE)

### Server
```typescript
// Next.js App Router
export async function GET(req: Request) {
  const stream = new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      const send = (event: string, data: any) => {
        controller.enqueue(encoder.encode(
          `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`
        ));
      };

      // Subscribe to events
      const unsub = eventBus.subscribe((event) => send(event.type, event.data));
      req.signal.addEventListener('abort', () => unsub());
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
}
```

### Client
```typescript
const source = new EventSource('/api/events');
source.addEventListener('notification', (e) => {
  const data = JSON.parse(e.data);
  showNotification(data);
});
source.onerror = () => {
  // Browser auto-reconnects SSE
};
```

---

## Pub/Sub with Redis

```typescript
import Redis from 'ioredis';

const publisher = new Redis();
const subscriber = new Redis();

// Publish
await publisher.publish('channel:updates', JSON.stringify({ type: 'new_order', data }));

// Subscribe
subscriber.subscribe('channel:updates');
subscriber.on('message', (channel, message) => {
  const event = JSON.parse(message);
  broadcastToClients(event);
});
```

---

## Optimistic Updates

```typescript
function sendMessage(text: string) {
  const tempId = crypto.randomUUID();

  // 1. Optimistically add to local state
  addMessage({ id: tempId, text, status: 'sending' });

  // 2. Send to server
  ws.send(JSON.stringify({ type: 'chat:message', payload: { text, tempId } }));

  // 3. On server confirmation, replace temp with real
  // Server responds: { type: 'chat:confirmed', payload: { tempId, realId } }
}

function handleConfirmation({ tempId, realId }: { tempId: string; realId: string }) {
  updateMessage(tempId, { id: realId, status: 'sent' });
}

function handleFailure({ tempId }: { tempId: string }) {
  updateMessage(tempId, { status: 'failed' });
}
```

---

## Presence System

```typescript
// Track online users per room
class PresenceManager {
  private presence = new Map<string, Set<string>>(); // roomId → Set<userId>

  join(roomId: string, userId: string) {
    if (!this.presence.has(roomId)) this.presence.set(roomId, new Set());
    this.presence.get(roomId)!.add(userId);
    this.broadcast(roomId, { type: 'presence:join', userId });
  }

  leave(roomId: string, userId: string) {
    this.presence.get(roomId)?.delete(userId);
    this.broadcast(roomId, { type: 'presence:leave', userId });
  }

  getOnline(roomId: string): string[] {
    return [...(this.presence.get(roomId) ?? [])];
  }
}
```

---

## Scaling Considerations

| Challenge | Solution |
|-----------|----------|
| Multiple server instances | Redis Pub/Sub or NATS for cross-instance messaging |
| Connection limits | Sticky sessions + horizontal scaling |
| Message ordering | Sequence numbers per channel |
| Deduplication | Client-side message ID tracking |
| Backpressure | Rate limit per client, message queuing |
| State recovery | Replay last N messages on reconnect |
