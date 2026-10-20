const select = (query) => document.querySelector(query);
const form = select("#create-form");
const styleInfo = {
  story: { photo: "forest", quote: "Có những ngày,<br>chậm lại cũng là<br><em>một cách đi xa.</em>" },
  healing: { photo: "journey", quote: "Bạn không cần<br>phải ổn,<br><em>trong mọi lúc.</em>" },
  wisdom: { photo: "lake", quote: "Nước càng sâu,<br>càng lặng.<br><em>Người cũng vậy.</em>" },
  talk: { photo: "forest", quote: "Có những thiệt thòi<br>chẳng ai nhìn thấy,<br><em>trừ người trong cuộc.</em>" },
};
const layoutNotes = {
  full: "Ảnh phủ kín màn hình, máy quay chuyển động, tít giật 3 giây đầu.",
  frame: "Nền giấy, tít vàng cố định ở trên, ảnh ngang ở giữa, phụ đề ngắn và bướm bay. Hợp với “Tâm sự đời”.",
};
const statusLabels = { done: "Đã hoàn tất", running: "Đang tạo", queued: "Đang chuẩn bị", error: "Cần thử lại", cancelled: "Đã dừng", interrupted: "Bị gián đoạn", waiting_images: "Chờ ảnh Gemini" };
const imageNotes = {
  codex: "Codex trên máy tự vẽ ảnh riêng cho từng cảnh bằng gói ChatGPT của bạn, không tốn thêm tiền. Khoảng 3 phút mỗi ảnh.",
  gemini: "Studio chia cảnh theo giọng đọc và viết prompt từng ảnh. Bạn dán vào Gemini, tải ảnh về; studio tự xếp và dựng.",
  library: "AI chọn ảnh thiên nhiên có sẵn từ Unsplash, chạy tự động từ đầu đến cuối.",
};
const downloadNotes = {
  ok: "Đang theo dõi thư mục Tải về: ảnh Gemini bạn tải sẽ tự vào cảnh trống đầu tiên.",
  denied: "macOS chưa cho studio đọc thư mục Tải về. Kéo thả hoặc dán ảnh (⌘V) vào từng cảnh nhé.",
};
let selectedJob = null;
let jobList = [];
let polling = false;
let busy = false;
let toastTimer;
let renderedScript = "";
let librarySignature = "";
let activeScene = null;

async function api(path, options = {}) {
  const response = await fetch(path, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
    signal: AbortSignal.timeout(15000),
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Có lỗi kết nối. Thử lại nhé.");
  return data;
}

function toast(message) {
  clearTimeout(toastTimer);
  select("#toast").textContent = message;
  select("#toast").hidden = false;
  toastTimer = setTimeout(() => { select("#toast").hidden = true; }, 5000);
}

function setView(view) {
  select("#create-view").hidden = view !== "create";
  select("#library-view").hidden = view !== "library";
  select("#nav-create").classList.toggle("active", view === "create");
  select("#nav-library").classList.toggle("active", view === "library");
  select("#breadcrumb").textContent = view === "create" ? "Tạo video mới" : "Thư viện của tôi";
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updatePreview() {
  if (selectedJob) return;
  const values = new FormData(form);
  const style = styleInfo[values.get("style")];
  const framed = values.get("layout") === "frame";
  select("#phone-preview").classList.toggle("framed", framed);
  select("#phone-preview").style.backgroundImage = `url('/static/photos/${framed ? "frame-preview" : style.photo}.jpg')`;
  select("#layout-note").textContent = layoutNotes[values.get("layout")];
  select("#channel").hidden = !framed;
  select("#preview-quote").innerHTML = `<span class="quote-stroke"></span><p>${style.quote}</p><span class="preview-caption">MỘT CHÚT CHIÊM NGHIỆM MỖI NGÀY</span>`;
  select("#preview-duration").textContent = `~${values.get("duration")} giây`;
  select("#image-source-note").textContent = imageNotes[values.get("images")];
}

const formatSeconds = value => `${value.toFixed(1).replace(".", ",")}s`;
const missingImages = job => (job.storyboard || []).filter(item => !item.image).length;
const isEditable = job => !["running", "queued"].includes(job.status);
const isDrawn = job => ["codex", "gemini"].includes(job.options.images);

function renderScript(job) {
  if (!job.script) {
    select("#script-section").hidden = true;
    return;
  }
  select("#script-section").hidden = false;
  const board = isDrawn(job) ? job.storyboard : null;
  updateRenderControls(job);
  const signature = job.id + JSON.stringify(board || job.script) + isEditable(job);
  if (renderedScript === signature) return;
  renderedScript = signature;
  select("#script-title").textContent = job.script.title;
  select("#gemini-guide").hidden = !board || job.status !== "waiting_images";
  const scenes = select("#scene-list");
  scenes.classList.toggle("storyboard", Boolean(board));
  scenes.replaceChildren(...(board
    ? board.map(item => storyboardScene(job, item))
    : job.script.scenes.map((scene, index) => plainScene(scene, index))));
}

function plainScene(scene, index) {
  const item = document.createElement("article");
  item.className = "scene-item";
  if (scene.photo) {
    const image = document.createElement("img");
    image.src = `/static/photos/${scene.photo}.jpg`;
    image.alt = `Ảnh minh họa cảnh ${index + 1}`;
    image.loading = "lazy";
    item.append(image);
  }
  const content = document.createElement("div");
  const label = document.createElement("span");
  label.textContent = `CẢNH ${String(index + 1).padStart(2, "0")}`;
  const paragraph = document.createElement("p");
  paragraph.textContent = scene.text;
  content.append(label, paragraph);
  item.append(content);
  return item;
}

function storyboardScene(job, item) {
  const editable = isEditable(job);
  const card = document.createElement("article");
  card.className = "scene-item board-item";
  const slot = document.createElement("button");
  slot.type = "button";
  slot.className = "scene-slot";
  slot.disabled = !editable;
  slot.setAttribute("aria-label", `${item.image ? "Đổi" : "Chọn"} ảnh cho cảnh ${item.scene}`);
  if (item.image) {
    const image = document.createElement("img");
    image.src = `/media/${job.id}/scene-${item.scene}.jpg?v=${item.image}`;
    image.alt = "";
    slot.append(image);
  } else {
    slot.innerHTML = '<svg><use href="#i-download"/></svg><span>Kéo thả, dán ⌘V<br>hoặc bấm chọn ảnh</span>';
  }
  const body = document.createElement("div");
  body.className = "board-body";
  const label = document.createElement("span");
  label.textContent = `CẢNH ${String(item.scene).padStart(2, "0")} · ${formatSeconds(item.start)} → ${formatSeconds(item.end)}`;
  const text = document.createElement("p");
  text.textContent = item.text;
  const details = document.createElement("details");
  const summary = document.createElement("summary");
  summary.textContent = "Prompt cho Gemini";
  const prompt = document.createElement("pre");
  prompt.textContent = item.prompt;
  details.append(summary, prompt);
  const actions = document.createElement("div");
  actions.className = "scene-actions";
  const copy = document.createElement("button");
  copy.type = "button";
  copy.className = "secondary-button";
  copy.textContent = "Sao chép prompt";
  copy.onclick = () => copyPrompt(item, copy);
  actions.append(copy);
  if (item.image && editable) {
    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "text-button";
    clear.textContent = "Bỏ ảnh";
    clear.onclick = () => clearImage(job.id, item.scene);
    actions.append(clear);
  }
  body.append(label, text, details, actions);
  card.append(slot, body);
  if (editable) {
    slot.onclick = () => chooseImage(job.id, item.scene);
    card.addEventListener("dragover", event => { event.preventDefault(); card.classList.add("dragging"); });
    card.addEventListener("dragleave", () => card.classList.remove("dragging"));
    card.addEventListener("drop", event => {
      event.preventDefault();
      card.classList.remove("dragging");
      const file = [...event.dataTransfer.files].find(entry => entry.type.startsWith("image/"));
      if (file) uploadImage(job.id, item.scene, file);
      else toast("Hãy tải ảnh về rồi kéo file vào, hoặc sao chép ảnh trong Gemini rồi dán ⌘V.");
    });
  }
  return card;
}

async function copyPrompt(item, button) {
  activeScene = item.scene;
  try {
    await navigator.clipboard.writeText(item.prompt);
    button.textContent = "Đã chép ✓";
    setTimeout(() => { button.textContent = "Sao chép prompt"; }, 2000);
    toast(`Đã chép prompt cảnh ${item.scene}. Dán vào Gemini nhé.`);
  } catch {
    toast("Trình duyệt chặn sao chép. Mở mục Prompt cho Gemini và chép tay nhé.");
  }
}

function chooseImage(jobId, scene) {
  const input = document.createElement("input");
  input.type = "file";
  input.accept = "image/*";
  input.onchange = () => uploadImage(jobId, scene, input.files[0]);
  input.click();
}

async function uploadImage(jobId, scene, file) {
  if (!file || !file.type.startsWith("image/")) return toast("Chỉ nhận file ảnh nhé.");
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, 2160 / bitmap.width, 3840 / bitmap.height);
    const canvas = document.createElement("canvas");
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext("2d").drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const portrait = bitmap.width / bitmap.height < 0.75;
    bitmap.close();
    const job = await api(`/api/jobs/${jobId}/scenes/${scene}/image`, {
      method: "POST", body: JSON.stringify({ image: canvas.toDataURL("image/jpeg", 0.92) }),
    });
    replaceJob(job);
    toast(portrait ? `Đã thêm ảnh cảnh ${scene}.` : `Đã thêm ảnh cảnh ${scene}. Ảnh không phải khung dọc nên sẽ bị cắt bớt hai bên.`);
  } catch (error) {
    toast(error.message || "Không đọc được ảnh này.");
  }
}

async function clearImage(jobId, scene) {
  try {
    replaceJob(await api(`/api/jobs/${jobId}/scenes/${scene}/clear`, { method: "POST", body: "{}" }));
  } catch (error) { toast(error.message); }
}

async function importDownloads(job) {
  try {
    const result = await api(`/api/jobs/${job.id}/import`, { method: "POST", body: "{}" });
    select("#downloads-status").textContent = downloadNotes[result.downloads] || "";
    if (result.imported.length) toast(`Đã lấy ảnh từ Tải về cho cảnh ${result.imported.map(item => item.scene).join(", ")}.`);
    return result.job;
  } catch {
    return job;
  }
}

function replaceJob(job) {
  jobList = jobList.map(item => item.id === job.id ? job : item);
  if (job.id === selectedJob) renderJob(job);
}

function updateRenderControls(job) {
  const board = isDrawn(job) && job.storyboard;
  const waiting = job.status === "waiting_images";
  const missing = board ? missingImages(job) : 0;
  select("#storyboard-actions").hidden = !(board && (waiting || (job.status === "done" && job.stale)));
  select("#waiting-actions").hidden = !waiting;
  for (const button of document.querySelectorAll(".render-button")) {
    const codex = job.options.images === "codex";
    button.disabled = missing > 0 && !codex;
    button.querySelector("span").textContent = missing ? (codex ? `Cho Codex vẽ tiếp ${missing} ảnh` : `Còn thiếu ${missing} ảnh`)
      : job.status === "done" ? "Dựng lại với ảnh mới" : "Dựng video";
  }
  select("#render-hint").textContent = missing ? "Thêm đủ ảnh cho mọi cảnh rồi dựng video."
    : "Dựng trên máy của bạn, thường mất khoảng một phút.";
}

async function renderVideo() {
  document.querySelectorAll(".render-button").forEach(button => { button.disabled = true; });
  try {
    renderJob(await api(`/api/jobs/${selectedJob}/render`, { method: "POST", body: "{}" }));
    await refresh();
    select(".preview-panel").scrollIntoView({ behavior: "smooth" });
  } catch (error) {
    toast(error.message);
    const job = jobList.find(item => item.id === selectedJob);
    if (job) updateRenderControls(job);
  }
}

function renderJob(job) {
  selectedJob = job.id;
  localStorage.setItem("lang-selected-job", job.id);
  const active = ["running", "queued"].includes(job.status);
  const completed = job.status === "done";
  const failed = ["error", "cancelled", "interrupted"].includes(job.status);
  const phone = select("#phone-preview");
  phone.classList.toggle("generating", active);
  phone.classList.toggle("is-video", completed);
  phone.classList.toggle("waiting", job.status === "waiting_images");
  phone.classList.toggle("framed", job.options.layout === "frame");
  if (job.cover) phone.style.backgroundImage = `url('${job.cover}')`;
  select("#progress-card").hidden = completed;
  select("#preview-meta").hidden = true;
  select("#progress-title").textContent = statusLabels[job.status] || "Đang xử lý";
  select("#progress-percent").textContent = `${job.progress}%`;
  select("#progress-fill").style.width = `${job.progress}%`;
  select("#progress-message").textContent = job.error || job.message;
  select("#cancel-button").hidden = !active;
  select("#cancel-button").disabled = false;
  select("#cancel-button").textContent = "Dừng tạo video";
  select("#retry-button").hidden = !failed;
  select("#retry-button").disabled = false;
  select("#result-actions").hidden = !completed;
  const video = select("#video-player");
  video.hidden = !completed;
  if (completed) {
    if (video.getAttribute("src") !== job.video) video.src = job.video;
    select("#download-video").href = `/media/${job.id}/final.mp4?download=1`;
    select("#download-script").href = `/media/${job.id}/script.txt?download=1`;
    select("#download-subtitles").href = `/media/${job.id}/subtitles.srt?download=1`;
    select("#download-sources").href = `/media/${job.id}/sources.json?download=1`;
    select("#result-info").textContent = `${job.duration}s · ${job.size} MB · MP4 720 × 1280`;
  } else {
    video.pause();
  }
  renderScript(job);
}

function resetPreview() {
  selectedJob = null;
  localStorage.removeItem("lang-selected-job");
  const video = select("#video-player");
  video.pause();
  video.removeAttribute("src");
  video.load();
  video.hidden = true;
  select("#phone-preview").classList.remove("is-video", "generating", "waiting");
  select("#progress-card").hidden = true;
  select("#result-actions").hidden = true;
  select("#script-section").hidden = true;
  select("#preview-meta").hidden = false;
  select("#downloads-status").textContent = "";
  activeScene = null;
  updatePreview();
}

function renderLibrary() {
  const signature = JSON.stringify(jobList.map(job => [job.id, job.status, job.title, job.cover, job.duration]));
  if (signature === librarySignature) return;
  librarySignature = signature;
  const container = select("#library-grid");
  select("#library-count").textContent = jobList.filter(job => job.status === "done").length;
  container.replaceChildren();
  if (!jobList.length) {
    container.innerHTML = '<div class="empty-library"><svg><use href="#i-film"/></svg><h2>Câu chuyện đầu tiên đang đợi bạn.</h2><p>Tạo một video, và nó sẽ ở đây khi bạn quay lại.</p><button class="primary-button" id="empty-create">Kể câu chuyện đầu tiên →</button></div>';
    select("#empty-create").onclick = () => setView("create");
    return;
  }
  jobList.forEach(job => {
    const card = document.createElement("button");
    card.className = "library-card";
    const imageWrap = document.createElement("div");
    imageWrap.className = "library-image";
    const image = document.createElement("img");
    image.src = job.cover || `/static/photos/${styleInfo[job.options.style].photo}.jpg`;
    image.alt = "";
    image.loading = "lazy";
    const status = document.createElement("span");
    status.textContent = statusLabels[job.status] || job.status;
    imageWrap.append(image, status);
    const copy = document.createElement("div");
    copy.className = "library-copy";
    const title = document.createElement("h3");
    title.textContent = job.title;
    const meta = document.createElement("p");
    meta.textContent = `${new Date(job.created).toLocaleDateString("vi-VN")} · ${job.duration ? `${job.duration}s` : `~${job.options.duration}s`} · ${job.options.provider === "claude" ? "Claude" : "Codex"}`;
    copy.append(title, meta);
    card.append(imageWrap, copy);
    card.onclick = () => { renderJob(job); setView("create"); };
    container.append(card);
  });
}

async function refresh() {
  if (polling) return;
  polling = true;
  try {
    jobList = await api("/api/jobs");
    busy = jobList.some(job => ["running", "queued"].includes(job.status));
    select("#generate").disabled = busy;
    select("#generate span").textContent = busy ? "Đang tạo thước phim…" : "Tạo thước phim của tôi";
    let job = jobList.find(item => item.id === selectedJob);
    if (job && job.status === "waiting_images" && missingImages(job)) {
      job = await importDownloads(job);
      jobList = jobList.map(item => item.id === job.id ? job : item);
    }
    if (job) renderJob(job);
    renderLibrary();
  } catch {
    if (busy) toast("Mất kết nối với studio. Giữ Terminal mở; web sẽ tự kết nối lại.");
  } finally {
    polling = false;
  }
}

form.addEventListener("submit", async event => {
  event.preventDefault();
  if (busy) return;
  const values = new FormData(form);
  const payload = {
    topic: values.get("topic").trim(),
    style: values.get("style"),
    duration: Number(values.get("duration")),
    voice: values.get("voice"),
    provider: values.get("provider"),
    images: values.get("images"),
    layout: values.get("layout"),
    channel: values.get("channel") || "",
    music: select("#music").checked,
    subtitles: select("#subtitles").checked,
  };
  select("#form-error").hidden = true;
  busy = true;
  select("#generate").disabled = true;
  try {
    const job = await api("/api/jobs", { method: "POST", body: JSON.stringify(payload) });
    renderJob(job);
    toast("Đã bắt đầu. Bạn có thể xem tiến trình ngay bên cạnh.");
    await refresh();
    if (window.innerWidth < 700) select(".preview-panel").scrollIntoView({ behavior: "smooth" });
  } catch (error) {
    select("#form-error").textContent = error.message;
    select("#form-error").hidden = false;
    busy = false;
    select("#generate").disabled = false;
  }
});

select("#topic").addEventListener("input", () => {
  select("#character-count").textContent = `${select("#topic").value.length}/600`;
  localStorage.setItem("lang-topic", select("#topic").value);
});
form.addEventListener("change", event => {
  if (event.target.name === "style") {
    select(`input[name="layout"][value="${event.target.value === "talk" ? "frame" : "full"}"]`).checked = true;
  }
  updatePreview();
});
document.querySelectorAll("[data-topic]").forEach(button => {
  button.onclick = () => {
    select("#topic").value = button.dataset.topic;
    select("#topic").dispatchEvent(new Event("input"));
    select("#topic").focus();
  };
});
select("#nav-create").onclick = () => {
  if (!busy) resetPreview();
  setView("create");
};
select("#nav-library").onclick = () => { renderLibrary(); setView("library"); };
select("#help-button").onclick = () => select("#help-dialog").showModal();
select("#close-help").onclick = () => select("#help-dialog").close();
select("#help-dialog").addEventListener("click", event => {
  if (event.target === select("#help-dialog")) {
    const bounds = event.target.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) event.target.close();
  }
});
select("#cancel-button").onclick = async () => {
  select("#cancel-button").disabled = true;
  try {
    await api(`/api/jobs/${selectedJob}/cancel`, { method: "POST", body: "{}" });
    select("#cancel-button").textContent = "Đang dừng…";
  } catch (error) { toast(error.message); select("#cancel-button").disabled = false; }
};
document.querySelectorAll(".render-button").forEach(button => { button.onclick = renderVideo; });
select("#storyboard-link").onclick = () => select("#script-section").scrollIntoView({ behavior: "smooth" });
document.addEventListener("paste", event => {
  const job = jobList.find(item => item.id === selectedJob);
  const file = [...(event.clipboardData?.files || [])].find(entry => entry.type.startsWith("image/"));
  if (!file || !job?.storyboard || !isDrawn(job) || !isEditable(job)) return;
  event.preventDefault();
  const empty = job.storyboard.filter(item => !item.image).map(item => item.scene);
  const scene = empty.includes(activeScene) ? activeScene : empty[0] || activeScene || job.storyboard.length;
  uploadImage(job.id, scene, file);
});
select("#retry-button").onclick = async () => {
  select("#retry-button").disabled = true;
  try {
    const job = await api(`/api/jobs/${selectedJob}/retry`, { method: "POST", body: "{}" });
    renderJob(job);
    await refresh();
  } catch (error) { toast(error.message); select("#retry-button").disabled = false; }
};

async function initialize() {
  select("#topic").value = localStorage.getItem("lang-topic") || "";
  select("#topic").dispatchEvent(new Event("input"));
  selectedJob = localStorage.getItem("lang-selected-job");
  try {
    const health = await api("/api/health");
    for (const provider of ["claude", "codex"]) {
      select(`#provider option[value="${provider}"]`).disabled = !health.providers[provider];
    }
    if (!health.providers.claude && health.providers.codex) select("#provider").value = "codex";
    if (!health.providers.codex) {
      select('input[name="images"][value="codex"]').disabled = true;
      select('input[name="images"][value="gemini"]').checked = true;
    }
    if (!health.providers.claude && !health.providers.codex) toast("Cần cài và đăng nhập Claude Code hoặc Codex để tạo kịch bản.");
    if (!health.ffmpeg || !health.font) toast("Máy đang thiếu FFmpeg hoặc font. Xem README để hoàn tất cài đặt.");
    await refresh();
    if (!selectedJob) {
      const active = jobList.find(job => ["running", "queued"].includes(job.status));
      if (active) renderJob(active);
    }
  } catch { toast("Chưa kết nối được studio. Hãy mở lại Mo Lang Studio.command."); }
  updatePreview();
  setInterval(refresh, 2500);
}

initialize();
