import { useEffect, useState } from "react";

const enabled = import.meta.env.VITE_SPOT_LOCAL_CHAT === "1";
const KEY_SLOT = "starfleet.localChat.ogre";
const validKey = /^[0-9a-f]{64}$/;

async function localRequest(key, session, payload, signal) {
  const response = await fetch(`/local-chat/${session}`, {
    method: payload ? "POST" : "GET",
    headers: {
      Authorization: `Bearer ${key}`,
      ...(payload ? { "Content-Type": "application/json" } : {}),
    },
    body: payload ? JSON.stringify(payload) : undefined,
    cache: "no-store",
    signal,
  });
  if (!response.ok) {
    if (response.status === 401) throw new Error("Local Ogre key was rejected.");
    if (response.status === 409) throw new Error("Conversation changed. Reload before retrying.");
    throw new Error("Local chat is unavailable.");
  }
  return response.json();
}

export function useLocalChat(panel, restoreMessages) {
  const [key, setKey] = useState(() => enabled ? (sessionStorage.getItem(KEY_SLOT) || "") : "");
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const slot = `starfleet.localChat.session.${panel}`;

  useEffect(() => {
    if (!key) return;
    const controller = new AbortController();
    async function restore() {
      try {
        if (!window.isSecureContext) throw new Error("Local chat requires a secure browser origin.");
        let session = sessionStorage.getItem(slot);
        if (!session) {
          session = crypto.randomUUID().replaceAll("-", "");
          sessionStorage.setItem(slot, session);
        }
        const data = await localRequest(key, session, null, controller.signal);
        if (controller.signal.aborted) return;
        restoreMessages(data.messages);
        setReady(true);
      } catch (err) {
        if (!controller.signal.aborted) setError(err.message);
      }
    }
    restore();
    return () => controller.abort();
  }, [key, slot, restoreMessages]);

  function signIn(value) {
    const candidate = value.trim();
    if (!validKey.test(candidate)) {
      setError("Enter the 64-character local Ogre key.");
      return;
    }
    sessionStorage.setItem(KEY_SLOT, candidate);
    setError("");
    setReady(false);
    setKey(candidate);
  }

  function signOut() {
    sessionStorage.removeItem(KEY_SLOT);
    setKey("");
    setReady(false);
    setError("");
    restoreMessages([]);
  }

  return {
    enabled, selected: Boolean(key), ready, error, signIn, signOut,
    send: (payload) => localRequest(key, sessionStorage.getItem(slot), payload),
  };
}
