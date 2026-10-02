/**
 * Real microphone recording via the MediaRecorder API.
 *
 * This is the genuine "PARLER" step: the browser captures the professional's
 * voice and hands the audio bytes to the backend for real speech-to-text. If no
 * real STT engine is configured the backend says so; the UI never fabricates a
 * transcript from audio.
 *
 * Nothing is uploaded until the caller explicitly asks for the blob. Recording
 * is stopped and discarded if the user leaves the step.
 */
import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderState = "idle" | "requesting" | "recording" | "paused" | "stopped" | "error";

export interface Recorder {
  state: RecorderState;
  error: string | null;
  seconds: number;
  supported: boolean;
  start: () => Promise<void>;
  pause: () => void;
  resume: () => void;
  stop: () => Promise<Blob | null>;
  reset: () => void;
}

export function useRecorder(): Recorder {
  const supported =
    typeof window !== "undefined" &&
    typeof navigator !== "undefined" &&
    !!navigator.mediaDevices?.getUserMedia &&
    typeof MediaRecorder !== "undefined";

  const [state, setState] = useState<RecorderState>("idle");
  const [error, setError] = useState<string | null>(null);
  const [seconds, setSeconds] = useState(0);

  const mediaRecorder = useRef<MediaRecorder | null>(null);
  const chunks = useRef<BlobPart[]>([]);
  const stream = useRef<MediaStream | null>(null);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);
  const resolveStop = useRef<((blob: Blob | null) => void) | null>(null);

  const clearTimer = useCallback(() => {
    if (timer.current) {
      clearInterval(timer.current);
      timer.current = null;
    }
  }, []);

  const releaseStream = useCallback(() => {
    stream.current?.getTracks().forEach((t) => t.stop());
    stream.current = null;
  }, []);

  useEffect(() => {
    return () => {
      clearTimer();
      releaseStream();
    };
  }, [clearTimer, releaseStream]);

  const start = useCallback(async () => {
    if (!supported) {
      setState("error");
      setError("L'enregistrement audio n'est pas disponible dans ce navigateur.");
      return;
    }
    setError(null);
    setState("requesting");
    try {
      const s = await navigator.mediaDevices.getUserMedia({ audio: true });
      stream.current = s;
      chunks.current = [];
      const recorder = new MediaRecorder(s);
      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunks.current.push(e.data);
      };
      recorder.onstop = () => {
        const blob = chunks.current.length ? new Blob(chunks.current, { type: "audio/webm" }) : null;
        releaseStream();
        resolveStop.current?.(blob);
        resolveStop.current = null;
      };
      mediaRecorder.current = recorder;
      recorder.start();
      setSeconds(0);
      setState("recording");
      clearTimer();
      timer.current = setInterval(() => setSeconds((v) => v + 1), 1000);
    } catch {
      // Permission denied or no device: degrade honestly, never fake audio.
      setState("error");
      setError("Accès au microphone refusé ou indisponible.");
      releaseStream();
    }
  }, [supported, clearTimer, releaseStream]);

  const pause = useCallback(() => {
    if (mediaRecorder.current?.state === "recording") {
      mediaRecorder.current.pause();
      clearTimer();
      setState("paused");
    }
  }, [clearTimer]);

  const resume = useCallback(() => {
    if (mediaRecorder.current?.state === "paused") {
      mediaRecorder.current.resume();
      timer.current = setInterval(() => setSeconds((v) => v + 1), 1000);
      setState("recording");
    }
  }, []);

  const stop = useCallback((): Promise<Blob | null> => {
    clearTimer();
    return new Promise((resolve) => {
      const recorder = mediaRecorder.current;
      if (!recorder || recorder.state === "inactive") {
        releaseStream();
        setState("stopped");
        resolve(null);
        return;
      }
      resolveStop.current = resolve;
      recorder.stop();
      setState("stopped");
    });
  }, [clearTimer, releaseStream]);

  const reset = useCallback(() => {
    clearTimer();
    releaseStream();
    chunks.current = [];
    mediaRecorder.current = null;
    setSeconds(0);
    setError(null);
    setState("idle");
  }, [clearTimer, releaseStream]);

  return { state, error, seconds, supported, start, pause, resume, stop, reset };
}

/** Encode a Blob as base64 (no data: prefix) for JSON transport. */
export async function blobToBase64(blob: Blob): Promise<string> {
  const buffer = await blob.arrayBuffer();
  let binary = "";
  const bytes = new Uint8Array(buffer);
  const chunkSize = 0x8000;
  for (let i = 0; i < bytes.length; i += chunkSize) {
    binary += String.fromCharCode(...bytes.subarray(i, i + chunkSize));
  }
  return btoa(binary);
}
