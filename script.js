const moodStep = document.getElementById("moodStep");
const platformStep = document.getElementById("platformStep");
const resultStep = document.getElementById("resultStep");
const statusEl = document.getElementById("status");

const songCard = document.getElementById("songCard");
const songName = document.getElementById("songName");
const artistName = document.getElementById("artistName");
const sourceIcon = document.getElementById("sourceIcon");
const messageWrap = document.getElementById("messageWrap");
const messageText = document.getElementById("messageText");
const heartBurst = document.getElementById("heartBurst");
const youtubeWrap = document.getElementById("youtubeWrap");
const youtubePlayer = document.getElementById("youtubePlayer");

const backToMoodBtn = document.getElementById("backToMood");
const startOverBtn = document.getElementById("startOver");
const bgmToggleBtn = document.getElementById("bgmToggle");
const ambientAudio = document.getElementById("ambientAudio");

let selectedMood = "";

function setStep(stepId) {
  [moodStep, platformStep, resultStep].forEach((el) => el.classList.remove("active"));
  document.getElementById(stepId).classList.add("active");
}

function setStatus(text, isError = false) {
  statusEl.textContent = text || "";
  statusEl.style.color = isError ? "#b03864" : "";
}

function rippleButton(button, event) {
  const rect = button.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  button.style.setProperty("--rx", `${x}px`);
  button.style.setProperty("--ry", `${y}px`);
  button.classList.remove("ripple-animate");
  void button.offsetWidth;
  button.classList.add("ripple-animate");
}

function typeMessage(text) {
  messageText.textContent = "";
  const chars = Array.from(text);
  let i = 0;
  const totalMs = Math.max(500, chars.length * 24);

  const timer = setInterval(() => {
    messageText.textContent += chars[i] || "";
    i += 1;
    if (i >= chars.length) clearInterval(timer);
  }, 24);

  return totalMs;
}

function extractYouTubeId(url) {
  try {
    const parsed = new URL(url);
    if (parsed.hostname.includes("youtu.be")) return parsed.pathname.replace("/", "") || null;
    if (parsed.searchParams.get("v")) return parsed.searchParams.get("v");
    if (parsed.pathname.includes("/embed/")) return parsed.pathname.split("/embed/")[1] || null;
    return null;
  } catch {
    return null;
  }
}

async function callGenerateApi(mood, platform) {
  const response = await fetch("/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mood, platform }),
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }

  return response.json();
}

function renderResult(data, requestedPlatform) {
  setStep("resultStep");

  songName.textContent = data.song || "Unknown Song";
  artistName.textContent = data.artist || "Unknown Artist";

  const source = (data.source || requestedPlatform || "youtube").toLowerCase();
  sourceIcon.textContent = source === "spotify" ? "🎵" : "▶️";

  songCard.classList.add("hidden");
  messageWrap.classList.remove("hidden");
  heartBurst.classList.remove("hidden");
  const typingDuration = typeMessage(data.message || "Thinking of you ❤️");

  // Show message first, then reveal song card.
  setTimeout(() => {
    songCard.classList.remove("hidden");
  }, typingDuration + 1000);

  youtubeWrap.classList.add("hidden");
  youtubePlayer.removeAttribute("src");

  // Start playback only after message is visible.
  setTimeout(() => {
    if (source === "youtube" && data.url) {
      const videoId = extractYouTubeId(data.url);
      if (videoId) {
        youtubePlayer.src = `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;
        youtubeWrap.classList.remove("hidden");
      } else {
        window.open(data.url, "_blank", "noopener,noreferrer");
      }
    } else if (source === "spotify" && data.url) {
      window.open(data.url, "_blank", "noopener,noreferrer");
    }
  }, typingDuration + 2000);
}

async function handlePlatformSelect(platform) {
  if (!selectedMood) {
    setStatus("Please pick a mood first.", true);
    setStep("moodStep");
    return;
  }

  setStatus("Finding your song and writing a personal message...");

  try {
    const data = await callGenerateApi(selectedMood, platform);
    renderResult(data, platform);
    setStatus("Made with love ❤️");
  } catch (err) {
    setStatus("Could not reach backend /generate. Please start your server.", true);
    console.error(err);
  }
}

function wireButtons() {
  document.querySelectorAll(".choice-btn.ripple").forEach((btn) => {
    btn.addEventListener("click", (e) => rippleButton(btn, e));
  });

  document.querySelectorAll("[data-mood]").forEach((btn) => {
    btn.addEventListener("click", () => {
      selectedMood = btn.dataset.mood;
      setStep("platformStep");
      setStatus(`Mood selected: ${selectedMood}`);
    });
  });

  document.querySelectorAll("[data-platform]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const platform = btn.dataset.platform;
      handlePlatformSelect(platform);
    });
  });

  backToMoodBtn.addEventListener("click", () => {
    setStep("moodStep");
    setStatus("");
  });

  startOverBtn.addEventListener("click", () => {
    setStep("moodStep");
    selectedMood = "";
    songCard.classList.add("hidden");
    messageWrap.classList.add("hidden");
    youtubeWrap.classList.add("hidden");
    youtubePlayer.removeAttribute("src");
    setStatus("");
  });

  bgmToggleBtn.addEventListener("click", async () => {
    if (ambientAudio.paused) {
      try {
        ambientAudio.volume = 0.25;
        await ambientAudio.play();
        bgmToggleBtn.textContent = "🔊 Ambience On";
        bgmToggleBtn.setAttribute("aria-pressed", "true");
      } catch {
        setStatus("Browser blocked autoplay. Click toggle again to enable ambience.", true);
      }
    } else {
      ambientAudio.pause();
      bgmToggleBtn.textContent = "🔈 Ambience Off";
      bgmToggleBtn.setAttribute("aria-pressed", "false");
    }
  });
}

wireButtons();
setStep("moodStep");
