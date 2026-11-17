"use client";

import { useCallback, useEffect, useState } from "react";
import {
  IngressConfig,
  IngressStatus,
  UpdateIngressConfigInput,
} from "../../domain/ingress.model";
import { defaultIngressRepository } from "../api/ingress.api-repository";

export function useIngress(provider: string = "gmail") {
  const [config, setConfig] = useState<IngressConfig | null>(null);
  const [status, setStatus] = useState<IngressStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [syncing, setSyncing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [cfg, stat] = await Promise.all([
        defaultIngressRepository.getConfig(provider),
        defaultIngressRepository.getStatus(provider),
      ]);
      setConfig(cfg);
      setStatus(stat);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load ingress configuration");
    } finally {
      setLoading(false);
    }
  }, [provider]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const updateConfig = async (input: UpdateIngressConfigInput) => {
    setError(null);
    try {
      const updated = await defaultIngressRepository.updateConfig({
        ...input,
        provider,
      });
      setConfig(updated);
      setNotice("Ingress configuration updated successfully.");
      // Refresh status as well
      defaultIngressRepository.getStatus(provider).then(setStatus).catch(() => {});
      return updated;
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to update configuration");
      throw err;
    }
  };

  const triggerSync = async () => {
    setSyncing(true);
    setError(null);
    try {
      const result = await defaultIngressRepository.triggerSync(provider);
      setNotice(result.message || "Manual sync triggered successfully.");
      setConfig(result.config);
      await fetchData();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to trigger sync");
    } finally {
      setSyncing(false);
    }
  };

  return {
    config,
    status,
    loading,
    syncing,
    error,
    notice,
    refresh: fetchData,
    updateConfig,
    triggerSync,
  };
}
