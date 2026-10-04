class PcmDownsampler extends AudioWorkletProcessor {
  process(inputs) {
    const channel = inputs[0] && inputs[0][0];
    if (!channel || channel.length === 0) {
      return true;
    }

    const ratio = sampleRate / 16000;
    const outCount = Math.max(1, Math.floor(channel.length / ratio));
    const pcm = new Int16Array(outCount);

    for (let i = 0; i < outCount; i += 1) {
      const sourceIndex = i * ratio;
      const left = Math.min(Math.floor(sourceIndex), channel.length - 1);
      const right = Math.min(left + 1, channel.length - 1);
      const blend = sourceIndex - left;
      const sample = channel[left] * (1 - blend) + channel[right] * blend;
      const clipped = Math.max(-1, Math.min(1, sample));
      pcm[i] = clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff;
    }

    this.port.postMessage(pcm.buffer, [pcm.buffer]);
    return true;
  }
}

registerProcessor("pcm-downsampler", PcmDownsampler);
