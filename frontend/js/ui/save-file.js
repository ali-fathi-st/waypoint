/**
 * Save a generated file (the data export) to the user's computer.
 * A normal download link works on GitHub Pages and locally. Inside a
 * claude.ai artifact, plain downloads are blocked, so the viewer's own
 * download prompt is used when it's available.
 */
export async function saveFile(filename, blob) {
  if (typeof window.claude?.use === "function") {
    const downloads = await window.claude.use("downloads");
    if (downloads) {
      try {
        await downloads.save({ filename, data: blob });
        return "saved";
      } catch (e) {
        if (e?.code === "declined") return "declined";
        throw e;
      }
    }
  }
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  return "saved";
}
