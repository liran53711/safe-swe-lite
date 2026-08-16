let downloadUrl = null;

async function runDemo(name) {
  const traceEl = document.getElementById("trace");
  traceEl.textContent = "Running " + name + " demo (mock mode)...";
  const response = await fetch("/api/demo/" + name, { method: "POST" });
  const data = await response.json();
  if (!response.ok) {
    traceEl.textContent = "Error: " + JSON.stringify(data, null, 2);
    return;
  }
  traceEl.textContent = JSON.stringify(data, null, 2);
  if (downloadUrl) URL.revokeObjectURL(downloadUrl);
  downloadUrl = URL.createObjectURL(
    new Blob([JSON.stringify(data, null, 2)], { type: "application/json" })
  );
  document.getElementById("download").href = downloadUrl;
}

document.getElementById("fix-bug").onclick = () => runDemo("fix-bug");
document.getElementById("blocked").onclick = () => runDemo("blocked");
