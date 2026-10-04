const TARGET_RATE = 16_000;

export function resampleTo16k(input: Float32Array, fromRate: number): Float32Array {
  if (fromRate === TARGET_RATE) {
    return input;
  }
  if (fromRate <= 0 || input.length === 0) {
    return new Float32Array();
  }
  const ratio = fromRate / TARGET_RATE;
  const outCount = Math.max(1, Math.floor(input.length / ratio));
  const output = new Float32Array(outCount);
  for (let index = 0; index < outCount; index += 1) {
    const sourceIndex = index * ratio;
    const left = Math.min(Math.floor(sourceIndex), input.length - 1);
    const right = Math.min(left + 1, input.length - 1);
    const blend = sourceIndex - left;
    output[index] = input[left] * (1 - blend) + input[right] * blend;
  }
  return output;
}

export function floatToPcm16(input: Float32Array): Int16Array {
  const pcm = new Int16Array(input.length);
  for (let index = 0; index < input.length; index += 1) {
    const clipped = Math.max(-1, Math.min(1, input[index] ?? 0));
    pcm[index] = clipped < 0 ? clipped * 0x8000 : clipped * 0x7fff;
  }
  return pcm;
}

export function rmsLevel(samples: Float32Array): number {
  if (samples.length === 0) {
    return 0;
  }
  let sum = 0;
  for (let index = 0; index < samples.length; index += 1) {
    const value = samples[index] ?? 0;
    sum += value * value;
  }
  return Math.sqrt(sum / samples.length);
}
