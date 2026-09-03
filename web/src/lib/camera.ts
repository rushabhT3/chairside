export class CameraUnavailableError extends Error {
  constructor(cause: unknown) {
    super("The camera could not be opened. Allow camera access, or use the file picker.");
    this.cause = cause;
  }
}

const captureQuality = 0.92;

export async function startFrontCamera(video: HTMLVideoElement): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia) throw new CameraUnavailableError("unsupported");
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: "user", width: { ideal: 1600 }, height: { ideal: 1600 } },
      audio: false,
    });
    video.srcObject = stream;
    await video.play();
    return stream;
  } catch (error) {
    throw new CameraUnavailableError(error);
  }
}

export function stopStream(stream: MediaStream | null): void {
  stream?.getTracks().forEach((track) => track.stop());
}

export function captureFrame(video: HTMLVideoElement): Promise<Blob> {
  if (video.videoWidth === 0 || video.videoHeight === 0) {
    return Promise.reject(new Error("The camera is still starting. Wait a moment, then scan again."));
  }
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const context = canvas.getContext("2d");
  if (!context) return Promise.reject(new Error("2D canvas unavailable"));
  context.drawImage(video, 0, 0);
  return new Promise((resolve, reject) => {
    canvas.toBlob(
      (blob) => (blob ? resolve(blob) : reject(new Error("Capture produced no image"))),
      "image/jpeg",
      captureQuality,
    );
  });
}
