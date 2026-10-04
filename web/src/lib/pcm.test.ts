import { describe, expect, it } from "vitest";
import { floatToPcm16, resampleTo16k, rmsLevel } from "./pcm";

describe("resampleTo16k", () => {
  it("returns the same buffer at 16 kHz", () => {
    const input = new Float32Array([0, 0.5, 1]);
    expect(resampleTo16k(input, 16000)).toBe(input);
  });

  it("downsamples 48 kHz audio to 16 kHz", () => {
    const input = new Float32Array(48);
    input[0] = 1;
    input[47] = -1;
    const output = resampleTo16k(input, 48000);
    expect(output.length).toBe(16);
  });
});

describe("floatToPcm16", () => {
  it("clips and scales samples", () => {
    const pcm = floatToPcm16(new Float32Array([0, 1, -1, 2]));
    expect(Array.from(pcm)).toEqual([0, 32767, -32768, 32767]);
  });
});

describe("rmsLevel", () => {
  it("returns 0 for empty input", () => {
    expect(rmsLevel(new Float32Array())).toBe(0);
  });

  it("returns 1 for a full-scale square wave", () => {
    expect(rmsLevel(new Float32Array([1, -1, 1, -1]))).toBe(1);
  });
});
