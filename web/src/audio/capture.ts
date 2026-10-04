export class CaptureError extends Error {
  constructor(message: string) {
    super(message);
    this.name = "CaptureError";
  }
}

export async function captureTab(): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getDisplayMedia) {
    throw new CaptureError("This browser cannot capture a tab. Use Chrome on this laptop.");
  }

  const stream = await navigator.mediaDevices.getDisplayMedia({
    video: {
      frameRate: 20,
      width: { ideal: 1920 },
      height: { ideal: 1080 },
    },
    audio: {
      echoCancellation: false,
      noiseSuppression: false,
      autoGainControl: false,
      channelCount: 1,
    },
  });

  if (stream.getAudioTracks().length === 0) {
    stopStream(stream);
    throw new CaptureError(
      "No audio arrived. Share the Chrome tab with TikTok Live and tick “Share tab audio”.",
    );
  }

  return stream;
}

export async function captureMic(): Promise<MediaStream> {
  if (!navigator.mediaDevices?.getUserMedia) {
    throw new CaptureError("Microphone capture is not available in this browser.");
  }

  return navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      channelCount: 1,
    },
    video: false,
  });
}

export function stopStream(stream: MediaStream): void {
  for (const track of stream.getTracks()) {
    track.stop();
  }
}

export async function startPcmPump(
  stream: MediaStream,
  onChunk: (bytes: ArrayBuffer) => void,
  onLevel: (level: number) => void,
): Promise<() => Promise<void>> {
  const audioTrack = stream.getAudioTracks()[0];
  if (!audioTrack) {
    throw new CaptureError("The capture stream has no audio track.");
  }

  const ctx = new AudioContext();
  await ctx.audioWorklet.addModule("/pcm-processor.js");
  const source = ctx.createMediaStreamSource(new MediaStream([audioTrack]));
  const worklet = new AudioWorkletNode(ctx, "pcm-downsampler");
  const analyser = ctx.createAnalyser();
  analyser.fftSize = 512;
  const monitor = new Float32Array(analyser.fftSize);
  const silentGain = ctx.createGain();
  silentGain.gain.value = 0;

  source.connect(worklet);
  source.connect(analyser);
  worklet.connect(silentGain);
  silentGain.connect(ctx.destination);

  let pending = new Int16Array(0);
  const frameSamples = 3200;

  worklet.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
    const incoming = new Int16Array(event.data);
    const merged = new Int16Array(pending.length + incoming.length);
    merged.set(pending);
    merged.set(incoming, pending.length);
    pending = merged;
    while (pending.length >= frameSamples) {
      const slice = pending.slice(0, frameSamples);
      pending = pending.slice(frameSamples);
      onChunk(slice.buffer);
    }
    analyser.getFloatTimeDomainData(monitor);
    let sum = 0;
    for (const sample of monitor) {
      sum += sample * sample;
    }
    onLevel(Math.sqrt(sum / monitor.length));
  };

  return async () => {
    worklet.port.onmessage = null;
    source.disconnect();
    worklet.disconnect();
    analyser.disconnect();
    silentGain.disconnect();
    await ctx.close();
  };
}
