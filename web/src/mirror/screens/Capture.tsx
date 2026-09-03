import { useEffect, useRef, useState } from "react";
import { captureFrame, startFrontCamera, stopStream } from "../../lib/camera";
import { countFaces } from "../../lib/faceCount";
import { formatTime } from "../../lib/format";
import { resizeForUpload } from "../../lib/resize";
import { mirrorApi } from "../../lib/xano";
import { Button } from "../components/Button";
import { Notice } from "../components/Notice";
import { PhotoPicker } from "../components/PhotoPicker";
import { Skeleton } from "../components/Skeleton";
import { StepList } from "../components/StepList";
import type { StepItem } from "../components/StepList";
import { navigate } from "../router";
import { useMirrorActions, useMirrorState } from "../store";

type Phase = "camera" | "checking" | "uploading" | "analysing" | "blocked";

const analysisSteps = [
  { name: "Color tones", event: "color_tones.done" },
  { name: "Skin", event: "skin_hd.done" },
  { name: "Hair", event: "hair_diagnostics.done" },
  { name: "Face shape", event: "face_attributes.done" },
] as const;

const revealIntervalMs = 900;
const finishDelayMs = 700;

export function Capture() {
  const { status, consultation, retained } = useMirrorState();
  const { setCaptured } = useMirrorActions();
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const [phase, setPhase] = useState<Phase>("camera");
  const [cameraError, setCameraError] = useState<string | null>(null);
  const [blockReason, setBlockReason] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(0);

  useEffect(() => {
    const video = videoRef.current;
    if (!video || phase !== "camera") return;
    let cancelled = false;
    startFrontCamera(video)
      .then((stream) => {
        if (cancelled) stopStream(stream);
        else streamRef.current = stream;
      })
      .catch((error: Error) => setCameraError(error.message));
    return () => {
      cancelled = true;
      stopStream(streamRef.current);
      streamRef.current = null;
    };
  }, [phase]);

  useEffect(() => {
    if (phase !== "analysing") return;
    if (revealed >= analysisSteps.length) {
      const done = window.setTimeout(() => navigate("card"), finishDelayMs);
      return () => window.clearTimeout(done);
    }
    const timer = window.setTimeout(() => setRevealed((n) => n + 1), revealIntervalMs);
    return () => window.clearTimeout(timer);
  }, [phase, revealed]);

  if (status !== "ready" || !consultation) return <Skeleton lines={3} label="Preparing camera" />;

  const eventTs = (type: string): string | null => {
    const found = consultation.events.find((event) => event.type === type);
    return found ? formatTime(found.ts) : null;
  };

  const steps: StepItem[] = analysisSteps.map((step, index) => ({
    name: step.name,
    status: index < revealed ? "done" : index === revealed ? "running" : "pending",
    ts: index < revealed ? eventTs(step.event) : null,
  }));

  const processImage = async (image: Blob) => {
    setPhase("checking");
    const bitmap = await createImageBitmap(image);
    const faces = await countFaces(bitmap);
    bitmap.close();
    if (faces !== 1) {
      setBlockReason(faces === 0 ? "No face found. Face the camera and try again." : "One client per scan.");
      setPhase("blocked");
      return;
    }
    setPhase("uploading");
    const resized = await resizeForUpload(image);
    const api = mirrorApi();
    const ticket = await api.createScan(consultation.id);
    await api.uploadImage(ticket.upload_url, resized.image);
    await api.completeScan(ticket.scan_id, resized.sha256, retained);
    setCaptured({ ...resized, scan_id: ticket.scan_id });
    setRevealed(0);
    setPhase("analysing");
  };

  const failScan = (error: unknown) => {
    setBlockReason(error instanceof Error ? error.message : "The scan could not be read.");
    setPhase("blocked");
  };

  const onScan = async () => {
    const video = videoRef.current;
    if (!video) return;
    try {
      const frame = await captureFrame(video);
      stopStream(streamRef.current);
      await processImage(frame);
    } catch (error) {
      failScan(error);
    }
  };

  const onFile = async (file: File | undefined) => {
    if (!file) return;
    try {
      await processImage(file);
    } catch (error) {
      failScan(error);
    }
  };

  if (phase === "blocked") {
    return (
      <Notice tone="error" title={blockReason ?? "One client per scan."} action={{ label: "Try again", onClick: () => setPhase("camera") }}>
        <p>Step into the oval alone, then scan again.</p>
        <PhotoPicker onPick={(file) => void onFile(file)} />
      </Notice>
    );
  }

  if (phase === "analysing") {
    return (
      <section className="capture-progress">
        <p className="capture-progress-title">Reading your scan</p>
        <StepList steps={steps} />
      </section>
    );
  }

  if (phase === "checking" || phase === "uploading") {
    return <Skeleton lines={2} label={phase === "checking" ? "Checking the frame" : "Uploading"} />;
  }

  return (
    <section className="capture">
      <div className="capture-stage">
        <video ref={videoRef} className="capture-video" playsInline muted autoPlay />
        <span className="capture-guide" aria-hidden="true" />
      </div>
      {cameraError ? (
        <Notice tone="quiet" title="Camera unavailable on this device.">
          <p>{cameraError}</p>
          <PhotoPicker onPick={(file) => void onFile(file)} />
        </Notice>
      ) : (
        <div className="capture-actions">
          <p className="capture-hint">Face the oval. One selfie is enough.</p>
          <Button onClick={() => void onScan()}>Scan</Button>
        </div>
      )}
    </section>
  );
}
