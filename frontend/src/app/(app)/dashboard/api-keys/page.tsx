"use client";

import React, { useEffect, useState } from "react";
import { getSession } from "next-auth/react";

// Components
import { ApiKeyManager } from "@/components";

// Types
type APIKey = {
  id: string;
  name: string;
  key_prefix: string;
  created_at: string;
  status: string;
  scopes: string[];
};

export default function ApiKeysPage() {
  const [keys, setKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [newKey, setNewKey] = useState<string | null>(null);
  const [error, setError] = useState("");

  const [createName, setCreateName] = useState("");
  const [isCreating, setIsCreating] = useState(false);


  useEffect(() => {
    async function init() {
      setLoading(true);
      try {
        const session = await getSession();
        const token = (session as any)?.accessToken;

        const headers: Record<string, string> = {};
        if (token) {
          headers["Authorization"] = `Bearer ${token}`;
        }

        const resKeys = await fetch("/api/v1/api_keys", {
          headers,
        });
        
        if (resKeys.ok) {
          const keysData = await resKeys.json();
          setKeys(Array.isArray(keysData) ? keysData : []);
        } else {
           if (resKeys.status === 401) setError("Unauthorized. Please login again.");
        }
      } catch (err: any) {
        console.error(err);
        setError(err.message || "Failed to load");
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  const handleCreate = async () => {
    if (!createName) return;
    setIsCreating(true);
    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;

      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) {
        headers["Authorization"] = `Bearer ${token}`;
      }

      const res = await fetch("/api/v1/api_keys", {
        method: "POST",
        headers,
        body: JSON.stringify({
          name: createName,
          scopes: ["graph:read", "graph:write"],
        }),
      });

      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.detail || "Failed to create key");
      }

      const data = await res.json();
      setNewKey(data.full_key);
      setKeys([...keys, { ...data, status: "active" }]);
      setCreateName("");
    } catch (err: any) {
      alert(err.message || "Error creating key");
    } finally {
      setIsCreating(false);
    }
  };

  const handleRevoke = async (id: string) => {
    if (
      !confirm("Are you sure? This application will lose access immediately.")
    )
      return;
    try {
      const session = await getSession();
      const token = (session as any)?.accessToken;

      await fetch(`/api/v1/api_keys/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });

      setKeys(keys.filter((k) => k.id !== id));
    } catch (err) {
      alert("Error revoking key");
    }
  };

  return (
    <div className="space-y-4">
      <header className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-sm font-semibold text-slate-100">
            Developer Keys
          </h1>
          <p className="mt-1 text-xs text-slate-400">
            Manage API keys for accessing your FAIM graphs programmatically.
          </p>
        </div>
      </header>

      {loading && (
        <div className="text-xs text-slate-500 animate-pulse">
          Loading context...
        </div>
      )}

      <ApiKeyManager
        keys={keys}
        loading={loading}
        error={error}
        newKey={newKey}
        createName={createName}
        setCreateName={setCreateName}
        isCreating={isCreating}
        onCreate={handleCreate}
        onRevoke={handleRevoke}

      />
    </div>
  );
}
