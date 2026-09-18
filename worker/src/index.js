/**
 * mimo-session: Cloudflare Worker per la sincronizzazione real-time
 * delle sessioni di chat partecipata con persistenza duale (KV + memory cache).
 */

const MEMORY_CACHE = new Map();

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);

    // Gestione CORS preflight
    if (request.method === "OPTIONS") {
      return new Response(null, {
        headers: {
          "Access-Control-Allow-Origin": "*",
          "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
          "Access-Control-Allow-Headers": "Content-Type"
        }
      });
    }

    const corsHeaders = {
      "Access-Control-Allow-Origin": "*",
      "Content-Type": "application/json"
    };

    if (url.pathname === "/api/messages") {
      let room = url.searchParams.get("room") || "stanza-nerln";

      if (request.method === "GET") {
        const kvKey = `room:${room}`;
        let list = MEMORY_CACHE.get(room) || [];
        if (list.length === 0 && env.MIMO_STORE) {
          try {
            const stored = await env.MIMO_STORE.get(kvKey, { type: "json" });
            if (stored && Array.isArray(stored)) {
              list = stored;
              MEMORY_CACHE.set(room, list);
            }
          } catch (e) {}
        }
        return new Response(JSON.stringify(list), { headers: corsHeaders });
      }

      if (request.method === "POST") {
        try {
          const body = await request.json();
          if (!body || !body.text) {
            return new Response(JSON.stringify({ error: "Messaggio non valido" }), { status: 400, headers: corsHeaders });
          }

          if (body.room) {
            room = body.room;
          }
          const kvKey = `room:${room}`;

          let list = MEMORY_CACHE.get(room) || [];
          if (list.length === 0 && env.MIMO_STORE) {
            try {
              const stored = await env.MIMO_STORE.get(kvKey, { type: "json" });
              if (stored && Array.isArray(stored)) list = stored;
            } catch (e) {}
          }

          list.push(body);
          if (list.length > 100) list.shift();
          MEMORY_CACHE.set(room, list);

          if (env.MIMO_STORE) {
            ctx.waitUntil(env.MIMO_STORE.put(kvKey, JSON.stringify(list)));
          }

          return new Response(JSON.stringify({ success: true, count: list.length, room }), { headers: corsHeaders });
        } catch (e) {
          return new Response(JSON.stringify({ error: e.message }), { status: 500, headers: corsHeaders });
        }
      }
    }

    return new Response(JSON.stringify({ status: "mimo-session worker active", kv: !!env.MIMO_STORE }), { headers: corsHeaders });
  }
};
