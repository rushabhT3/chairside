const pad = document.getElementById("pad") as HTMLCanvasElement;
const signButton = document.getElementById("sign") as HTMLButtonElement;
const clearButton = document.getElementById("clear") as HTMLButtonElement;
const ctx = pad.getContext("2d") as CanvasRenderingContext2D;

const ink = getComputedStyle(document.documentElement).getPropertyValue("--ink").trim();
const strokeWidth = 2.5;
let drawing = false;
let hasInk = false;

ctx.lineWidth = strokeWidth;
ctx.lineCap = "round";
ctx.lineJoin = "round";
ctx.strokeStyle = ink;

function padPoint(event: PointerEvent): [number, number] {
  const rect = pad.getBoundingClientRect();
  const scaleX = pad.width / rect.width;
  const scaleY = pad.height / rect.height;
  return [(event.clientX - rect.left) * scaleX, (event.clientY - rect.top) * scaleY];
}

pad.addEventListener("pointerdown", (event) => {
  drawing = true;
  pad.setPointerCapture(event.pointerId);
  const [x, y] = padPoint(event);
  ctx.beginPath();
  ctx.moveTo(x, y);
});

pad.addEventListener("pointermove", (event) => {
  if (!drawing) return;
  const [x, y] = padPoint(event);
  ctx.lineTo(x, y);
  ctx.stroke();
  hasInk = true;
  signButton.disabled = false;
});

pad.addEventListener("pointerup", () => {
  drawing = false;
});

clearButton.addEventListener("click", () => {
  ctx.clearRect(0, 0, pad.width, pad.height);
  hasInk = false;
  signButton.disabled = true;
});

signButton.addEventListener("click", () => {
  if (!hasInk) return;
  window.parent.postMessage({ type: "chairside.signed", signed_at: new Date().toISOString() }, "*");
  signButton.disabled = true;
  signButton.textContent = "Signed";
});
