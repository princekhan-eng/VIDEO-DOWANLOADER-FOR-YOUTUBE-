/**
 * UltraTube 4K Studio - Client Application Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // DOM Elements
  const form = document.getElementById('analyze-form');
  const inputUrl = document.getElementById('input-url');
  const btnPaste = document.getElementById('btn-paste');
  const btnClear = document.getElementById('btn-clear');
  const btnAnalyze = document.getElementById('btn-analyze');
  const spinner = btnAnalyze.querySelector('.spinner');
  const btnText = btnAnalyze.querySelector('.btn-text');

  // Error Banner
  const errorBanner = document.getElementById('error-banner');
  const errorTitle = document.getElementById('error-title');
  const errorMessage = document.getElementById('error-message');
  const errorActions = document.getElementById('error-actions');
  const btnCloseError = document.getElementById('btn-close-error');
  const btnFixCookies = document.getElementById('btn-fix-cookies');

  // Cookie & Anti-Bot Modal Elements
  const btnCookieSettings = document.getElementById('btn-cookie-settings');
  const cookieModal = document.getElementById('cookie-modal');
  const btnCloseCookieModal = document.getElementById('btn-close-cookie-modal');
  const navCookieBadge = document.getElementById('nav-cookie-badge');
  const cookieStatusDot = document.getElementById('cookie-status-dot');
  const cookieStatusTitle = document.getElementById('cookie-status-title');
  const cookieStatusDesc = document.getElementById('cookie-status-desc');
  const btnTestConnection = document.getElementById('btn-test-connection');
  const cookieTextarea = document.getElementById('cookie-textarea');
  const fileCookieUpload = document.getElementById('file-cookie-upload');
  const btnSaveCookies = document.getElementById('btn-save-cookies');
  const btnClearCookies = document.getElementById('btn-clear-cookies');
  const testResultBox = document.getElementById('test-result-box');
  const testResultTitle = document.getElementById('test-result-title');
  const testResultDetails = document.getElementById('test-result-details');
  const testIcon = document.getElementById('test-icon');

  // Media Analysis Card
  const mediaCard = document.getElementById('media-card');
  const videoThumbnail = document.getElementById('video-thumbnail');
  const badgeDuration = document.getElementById('badge-duration');
  const badgeMaxRes = document.getElementById('badge-max-res');
  const videoTitle = document.getElementById('video-title');
  const videoChannel = document.getElementById('video-channel');
  const videoViews = document.getElementById('video-views');

  // Format Tabs & Grids
  const tabVideo = document.getElementById('tab-video');
  const tabAudio = document.getElementById('tab-audio');
  const paneVideo = document.getElementById('pane-video');
  const paneAudio = document.getElementById('pane-audio');
  const videoFormatsGrid = document.getElementById('video-formats-grid');
  const audioFormatsGrid = document.getElementById('audio-formats-grid');

  // Selected Action Bar
  const selectedBadge = document.getElementById('selected-badge');
  const selectedName = document.getElementById('selected-name');
  const selectedDesc = document.getElementById('selected-desc');
  const btnStartDownload = document.getElementById('btn-start-download');

  // Playlist Card
  const playlistCard = document.getElementById('playlist-card');
  const playlistTitle = document.getElementById('playlist-title');
  const playlistCount = document.getElementById('playlist-count');
  const playlistItemsList = document.getElementById('playlist-items-list');
  const btnBatch4k = document.getElementById('btn-batch-4k');

  // Progress Card
  const progressCard = document.getElementById('progress-card');
  const progressStage = document.getElementById('progress-stage');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const statPercent = document.getElementById('stat-percent');
  const statSpeed = document.getElementById('stat-speed');
  const statEta = document.getElementById('stat-eta');
  const statSize = document.getElementById('stat-size');
  const completedActions = document.getElementById('completed-actions');
  const btnBrowserDownload = document.getElementById('btn-browser-download');
  const btnOpenFolderCompleted = document.getElementById('btn-open-folder-completed');
  const btnDownloadAnother = document.getElementById('btn-download-another');

  // Navigation & History
  const btnOpenFolder = document.getElementById('btn-open-folder');
  const btnRefreshHistory = document.getElementById('btn-refresh-history');
  const historyList = document.getElementById('history-list');
  const historyEmpty = document.getElementById('history-empty');
  const toastContainer = document.getElementById('toast-container');

  // State
  let currentMediaData = null;
  let selectedFormat = '4k';
  let activeWebSocket = null;

  // Initialize
  fetchHistory();
  checkCookieStatus();

  // Input Clear Button Toggle
  inputUrl.addEventListener('input', () => {
    btnClear.classList.toggle('hidden', !inputUrl.value.trim());
  });

  btnClear.addEventListener('click', () => {
    inputUrl.value = '';
    btnClear.classList.add('hidden');
    inputUrl.focus();
  });

  // Paste from Clipboard
  btnPaste.addEventListener('click', async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        inputUrl.value = text.trim();
        btnClear.classList.remove('hidden');
        showToast('Link pasted from clipboard!', 'success');
        analyzeUrl(inputUrl.value);
      }
    } catch (err) {
      showToast('Clipboard permission denied or unavailable.', 'error');
    }
  });

  // Sample Tags Click
  document.querySelectorAll('.sample-tag').forEach(tag => {
    tag.addEventListener('click', () => {
      const url = tag.getAttribute('data-url');
      inputUrl.value = url;
      btnClear.classList.remove('hidden');
      analyzeUrl(url);
    });
  });

  // Form Submission
  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const url = inputUrl.value.trim();
    if (!url) return;
    analyzeUrl(url);
  });

  // Close Error Banner
  btnCloseError.addEventListener('click', () => {
    errorBanner.classList.add('hidden');
  });

  if (btnFixCookies) {
    btnFixCookies.addEventListener('click', () => {
      openCookieModal();
    });
  }

  // Tab Switching
  tabVideo.addEventListener('click', () => {
    tabVideo.classList.add('active');
    tabAudio.classList.remove('active');
    paneVideo.classList.add('active');
    paneAudio.classList.remove('active');
  });

  tabAudio.addEventListener('click', () => {
    tabAudio.classList.add('active');
    tabVideo.classList.remove('active');
    paneAudio.classList.add('active');
    paneVideo.classList.remove('active');
  });

  // Open Downloads Folder
  btnOpenFolder.addEventListener('click', openDownloadsFolder);
  if (btnOpenFolderCompleted) {
    btnOpenFolderCompleted.addEventListener('click', openDownloadsFolder);
  }

  // Refresh History
  btnRefreshHistory.addEventListener('click', fetchHistory);

  // Download Another Button
  btnDownloadAnother.addEventListener('click', () => {
    progressCard.classList.add('hidden');
    if (currentMediaData && !currentMediaData.is_playlist) {
      mediaCard.classList.remove('hidden');
    }
    inputUrl.select();
  });

  // =========================================================================
  // Anti-Bot & Cookie Modal Logic
  // =========================================================================
  function openCookieModal() {
    cookieModal.classList.remove('hidden');
    checkCookieStatus();
  }

  function closeCookieModal() {
    cookieModal.classList.add('hidden');
  }

  btnCookieSettings.addEventListener('click', openCookieModal);
  btnCloseCookieModal.addEventListener('click', closeCookieModal);
  cookieModal.addEventListener('click', (e) => {
    if (e.target === cookieModal) closeCookieModal();
  });

  // Modal Tabs switching
  document.querySelectorAll('.modal-tab').forEach(tab => {
    tab.addEventListener('click', () => {
      document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.modal-tab-content').forEach(c => c.classList.remove('active'));

      tab.classList.add('active');
      const targetId = tab.getAttribute('data-tab');
      const targetContent = document.getElementById(targetId);
      if (targetContent) targetContent.classList.add('active');
    });
  });

  // File upload reader for cookies.txt
  if (fileCookieUpload) {
    fileCookieUpload.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) return;
      const reader = new FileReader();
      reader.onload = (ev) => {
        cookieTextarea.value = ev.target.result;
        showToast(`Loaded ${file.name} (${file.size} bytes)`, 'success');
      };
      reader.readAsText(file);
    });
  }

  // Check Cookie Status API
  async function checkCookieStatus() {
    try {
      const res = await fetch('/api/cookies/status');
      const data = await res.json();
      if (res.ok) {
        if (data.has_cookies) {
          cookieStatusDot.className = 'status-indicator-dot dot-green';
          navCookieBadge.className = 'cookie-dot-badge badge-active';
          navCookieBadge.title = 'Anti-Bot Cookies Active';
          cookieStatusTitle.textContent = 'Active (Anti-Bot Authenticated)';
          cookieStatusDesc.textContent = `Custom cookies active (${data.cookie_size_bytes || 0} bytes). Full 4K & Cloud bypass active.`;
        } else {
          cookieStatusDot.className = 'status-indicator-dot dot-amber';
          navCookieBadge.className = 'cookie-dot-badge badge-fallback';
          navCookieBadge.title = 'Multi-Client EJS Solver Active';
          cookieStatusTitle.textContent = 'Multi-Client EJS Solver Active';
          cookieStatusDesc.textContent = data.message || 'Auto-solving bot challenges with Node.js & Multi-Client engine.';
        }
      }
    } catch (e) {
      console.warn('Cookie status check failed:', e);
    }
  }

  // Save Cookies API
  btnSaveCookies.addEventListener('click', async () => {
    const cookiesText = cookieTextarea.value.trim();
    if (!cookiesText) {
      showToast('Please paste your cookie text or upload a cookies.txt file.', 'error');
      return;
    }

    btnSaveCookies.disabled = true;
    try {
      const res = await fetch('/api/cookies/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cookies_text: cookiesText }),
      });
      const data = await res.json();
      if (res.ok) {
        showToast(data.message || 'Cookies saved & activated successfully!', 'success');
        checkCookieStatus();
      } else {
        showToast(data.detail || 'Failed to save cookies.', 'error');
      }
    } catch (err) {
      showToast('Error communicating with server.', 'error');
    } finally {
      btnSaveCookies.disabled = false;
    }
  });

  // Clear Cookies API
  btnClearCookies.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to remove your saved YouTube cookies?')) return;
    try {
      const res = await fetch('/api/cookies/clear', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        cookieTextarea.value = '';
        showToast(data.message || 'Cookies removed.', 'success');
        checkCookieStatus();
      } else {
        showToast(data.detail || 'Could not clear cookies.', 'error');
      }
    } catch (err) {
      showToast('Error communicating with server.', 'error');
    }
  });

  // Test Connection API
  btnTestConnection.addEventListener('click', async () => {
    btnTestConnection.disabled = true;
    btnTestConnection.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin"></i> Testing...';
    testResultBox.classList.add('hidden');

    try {
      const res = await fetch('/api/cookies/test', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: 'https://www.youtube.com/watch?v=LXb3EKWsInQ' }),
      });
      const data = await res.json();

      testResultBox.classList.remove('hidden');
      if (data.success) {
        testResultBox.className = 'test-result-box test-success';
        testIcon.className = 'fa-solid fa-circle-check';
        testResultTitle.textContent = 'Connection Verified! YouTube Bot Check Bypassed';
        testResultDetails.textContent = `Successfully verified video "${data.title}". Max resolution: ${data.max_resolution} (4K UHD: ${data.has_4k ? 'Yes' : 'No'}). Ready for lossless downloads!`;
        showToast('Connection verified successfully!', 'success');
        checkCookieStatus();
      } else {
        testResultBox.className = 'test-result-box test-failure';
        testIcon.className = 'fa-solid fa-triangle-exclamation';
        testResultTitle.textContent = 'Verification Failed';
        testResultDetails.textContent = data.message || data.error || 'YouTube returned a verification challenge. Try pasting fresh cookies in Tab 1.';
        showToast('Verification failed. Check test details.', 'error');
      }
    } catch (err) {
      testResultBox.classList.remove('hidden');
      testResultBox.className = 'test-result-box test-failure';
      testIcon.className = 'fa-solid fa-triangle-exclamation';
      testResultTitle.textContent = 'Server Error';
      testResultDetails.textContent = 'Could not contact verification endpoint: ' + err.message;
      showToast('Test failed to complete.', 'error');
    } finally {
      btnTestConnection.disabled = false;
      btnTestConnection.innerHTML = '<i class="fa-solid fa-bolt"></i> Test Connection';
    }
  });

  // =========================================================================
  // Media Analysis Function
  // =========================================================================
  async function analyzeUrl(url) {
    hideError();
    mediaCard.classList.add('hidden');
    playlistCard.classList.add('hidden');
    progressCard.classList.add('hidden');

    setLoading(true);

    try {
      const res = await fetch('/api/info', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });

      const data = await res.json();

      if (!res.ok) {
        let msg = 'Failed to extract video information.';
        let needsCookies = false;
        if (typeof data.detail === 'object' && data.detail !== null) {
          msg = data.detail.message || msg;
          needsCookies = data.detail.needs_cookies || false;
        } else if (typeof data.detail === 'string') {
          msg = data.detail;
          needsCookies = msg.toLowerCase().includes('bot') || msg.toLowerCase().includes('sign in');
        }
        const err = new Error(msg);
        err.needsCookies = needsCookies;
        throw err;
      }

      currentMediaData = data;

      if (data.is_playlist) {
        renderPlaylist(data);
      } else {
        renderSingleVideo(data);
      }

      showToast('Media analyzed successfully!', 'success');
    } catch (err) {
      showError('Analysis Failed', err.message || 'Could not fetch video info.', err.needsCookies);
    } finally {
      setLoading(false);
    }
  }

  // Render Single Video Card
  function renderSingleVideo(data) {
    videoThumbnail.src = data.thumbnail || '';
    badgeDuration.textContent = data.duration || '00:00';
    badgeMaxRes.textContent = data.max_resolution || '4K UHD';
    videoTitle.textContent = data.title;
    videoChannel.textContent = data.uploader;
    videoViews.textContent = `${data.view_count} views`;

    // Render Video Formats
    videoFormatsGrid.innerHTML = '';
    const videoPresets = data.video_presets || [];

    videoPresets.forEach((preset, idx) => {
      const card = document.createElement('div');
      card.className = `format-card ${idx === 0 ? 'selected' : ''}`;
      card.dataset.formatId = preset.id;
      card.dataset.name = preset.name;
      card.dataset.badge = preset.badge;
      card.dataset.desc = preset.description;

      card.innerHTML = `
        <div class="format-card-header">
          <span class="format-res-badge badge-${preset.badge_color || 'crimson'}">${preset.badge}</span>
          <span style="font-size: 11px; color: #94a3b8;"><i class="fa-solid fa-film"></i> ${preset.ext.toUpperCase()}</span>
        </div>
        <div class="format-card-title">${preset.name}</div>
        <div class="format-card-desc">${preset.description}</div>
      `;

      card.addEventListener('click', () => {
        document.querySelectorAll('.format-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        updateSelectedFormat(preset.id, preset.badge, preset.name, preset.description);
      });

      videoFormatsGrid.appendChild(card);
    });

    // Render Audio Formats
    audioFormatsGrid.innerHTML = '';
    const audioPresets = data.audio_presets || [];

    audioPresets.forEach(preset => {
      const card = document.createElement('div');
      card.className = 'format-card';
      card.dataset.formatId = preset.id;
      card.dataset.name = preset.name;
      card.dataset.badge = preset.badge;
      card.dataset.desc = preset.description;

      card.innerHTML = `
        <div class="format-card-header">
          <span class="format-res-badge badge-amber">${preset.badge}</span>
          <span style="font-size: 11px; color: #94a3b8;"><i class="fa-solid fa-music"></i> ${preset.ext.toUpperCase()}</span>
        </div>
        <div class="format-card-title">${preset.name}</div>
        <div class="format-card-desc">${preset.description}</div>
      `;

      card.addEventListener('click', () => {
        document.querySelectorAll('.format-card').forEach(c => c.classList.remove('selected'));
        card.classList.add('selected');
        updateSelectedFormat(preset.id, preset.badge, preset.name, preset.description);
      });

      audioFormatsGrid.appendChild(card);
    });

    if (videoPresets.length > 0) {
      const defaultPreset = videoPresets[0];
      updateSelectedFormat(defaultPreset.id, defaultPreset.badge, defaultPreset.name, defaultPreset.description);
    }

    mediaCard.classList.remove('hidden');
    mediaCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  // Render Playlist Card
  function renderPlaylist(data) {
    playlistTitle.textContent = data.title;
    playlistCount.textContent = `${data.playlist_count} videos found by ${data.uploader}`;
    playlistItemsList.innerHTML = '';

    (data.entries || []).forEach(item => {
      const itemEl = document.createElement('div');
      itemEl.className = 'playlist-item';
      itemEl.innerHTML = `
        <img src="${item.thumbnail || ''}" class="playlist-item-thumb" alt="">
        <span class="playlist-item-title">${item.index}. ${item.title}</span>
        <span class="playlist-item-dur">${item.duration}</span>
        <button class="btn btn-secondary btn-sm" onclick="downloadSingleFromPlaylist('${item.url}')">
          <i class="fa-solid fa-download"></i> 4K
        </button>
      `;
      playlistItemsList.appendChild(itemEl);
    });

    playlistCard.classList.remove('hidden');
    playlistCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  window.downloadSingleFromPlaylist = (url) => {
    inputUrl.value = url;
    analyzeUrl(url);
  };

  function updateSelectedFormat(id, badge, name, desc) {
    selectedFormat = id;
    selectedBadge.textContent = badge;
    selectedName.textContent = name;
    selectedDesc.textContent = desc;
  }

  // Batch Download All in 4K
  btnBatch4k.addEventListener('click', () => {
    if (!currentMediaData || !currentMediaData.entries) return;
    showToast(`Starting batch download of ${currentMediaData.entries.length} items in 4K...`, 'success');
    currentMediaData.entries.forEach(entry => {
      startDownloadTask(entry.url, '4k');
    });
  });

  // Start Single Download
  btnStartDownload.addEventListener('click', () => {
    const url = inputUrl.value.trim();
    if (!url) return;
    startDownloadTask(url, selectedFormat);
  });

  // Download Task Function
  async function startDownloadTask(url, formatId) {
    mediaCard.classList.add('hidden');
    progressCard.classList.remove('hidden');
    completedActions.classList.add('hidden');
    progressCard.scrollIntoView({ behavior: 'smooth', block: 'center' });

    progressBarFill.style.width = '0%';
    statPercent.textContent = '0%';
    statSpeed.textContent = 'Connecting...';
    statEta.textContent = '--';
    statSize.textContent = '0 MB / --';
    progressStage.textContent = 'Initiating download streams...';

    try {
      const res = await fetch('/api/download', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url, format_id: formatId }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || 'Could not queue download.');
      }

      connectProgressWebSocket(data.task_id);
    } catch (err) {
      showError('Download Failed', err.message);
    }
  }

  let progressPollTimer = null;

  function stopProgressTracking() {
    if (activeWebSocket) {
      try { activeWebSocket.close(); } catch(e) {}
      activeWebSocket = null;
    }
    if (progressPollTimer) {
      clearInterval(progressPollTimer);
      progressPollTimer = null;
    }
  }

  function startPollingProgress(taskId) {
    if (progressPollTimer) return;
    progressPollTimer = setInterval(async () => {
      try {
        const res = await fetch(`/api/progress/${taskId}`);
        if (res.ok) {
          const data = await res.json();
          handleProgressUpdate(data);
          if (data.status === 'completed' || data.status === 'error') {
            stopProgressTracking();
          }
        }
      } catch (err) {
        console.warn('Progress polling error:', err);
      }
    }, 1000);
  }

  // WebSocket Live Telemetry Connection with Automatic HTTP Polling Fallback
  function connectProgressWebSocket(taskId) {
    stopProgressTracking();

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/api/ws/progress/${taskId}`;

      activeWebSocket = new WebSocket(wsUrl);

      activeWebSocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          handleProgressUpdate(data);
          if (data.status === 'completed' || data.status === 'error') {
            stopProgressTracking();
          }
        } catch (e) {
          console.error('Error parsing WS message:', e);
        }
      };

      activeWebSocket.onerror = (err) => {
        console.warn('WebSocket unavailable on host, falling back to HTTP polling:', err);
        startPollingProgress(taskId);
      };

      activeWebSocket.onclose = () => {
        startPollingProgress(taskId);
      };
    } catch (e) {
      startPollingProgress(taskId);
    }
  }

  // Progress Update Handler
  function handleProgressUpdate(data) {
    if (data.percent !== undefined) {
      const p = Math.min(Math.max(data.percent, 0), 100);
      progressBarFill.style.width = `${p}%`;
      statPercent.textContent = `${p}%`;
    }

    if (data.speed_str) statSpeed.textContent = data.speed_str;
    if (data.eta_str) statEta.textContent = data.eta_str;
    if (data.downloaded_str || data.total_str) {
      statSize.textContent = `${data.downloaded_str || '0 MB'} / ${data.total_str || '--'}`;
    }
    if (data.stage) {
      progressStage.textContent = data.stage;
    }

    if (data.status === 'completed') {
      progressBarFill.style.width = '100%';
      statPercent.textContent = '100%';
      statSpeed.textContent = 'Completed';
      statEta.textContent = '0s';
      completedActions.classList.remove('hidden');

      if (data.download_url) {
        btnBrowserDownload.href = data.download_url;
        btnBrowserDownload.setAttribute('download', data.filename || 'download');
      }

      showToast('4K Download Complete & Merged!', 'success');
      fetchHistory();
    } else if (data.status === 'error') {
      progressStage.textContent = data.stage || 'An error occurred during download.';
      statSpeed.textContent = 'Error';
      showToast(data.error || 'Download failed.', 'error');
    }
  }

  // Open Downloads Folder API
  async function openDownloadsFolder() {
    try {
      const res = await fetch('/api/open-folder', { method: 'POST' });
      const data = await res.json();
      if (res.ok) {
        if (data.status === 'cloud' || data.status === 'info') {
          showToast(data.message || 'Running on cloud server. Direct download is used.', 'info');
        } else {
          showToast('Opened downloads folder.', 'success');
        }
      } else {
        showToast(data.detail || data.message || 'Could not open folder.', 'error');
      }
    } catch (err) {
      showToast('Failed to trigger folder opening.', 'error');
    }
  }

  // Fetch History API
  async function fetchHistory() {
    try {
      const res = await fetch('/api/history');
      const list = await res.json();

      historyList.innerHTML = '';
      if (!list || list.length === 0) {
        historyEmpty.classList.remove('hidden');
        return;
      }

      historyEmpty.classList.add('hidden');
      list.forEach(item => {
        const card = document.createElement('div');
        card.className = 'history-card';
        card.innerHTML = `
          <div class="history-item-left">
            <img src="${item.thumbnail || ''}" class="history-thumb" alt="">
            <div class="history-details">
              <span class="history-title" title="${item.title}">${item.title}</span>
              <div class="history-sub">
                <span class="format-res-badge badge-crimson">${item.format}</span>
                <span>${item.file_size}</span>
                <span>&bull;</span>
                <span>${item.download_date}</span>
              </div>
            </div>
          </div>
          <div class="history-item-actions">
            <a href="/api/files/${encodeURIComponent(item.filename)}" class="btn btn-secondary btn-sm" download title="Download to Device">
              <i class="fa-solid fa-download"></i>
            </a>
            <button class="btn btn-icon-small" onclick="deleteHistoryItem('${item.id}')" title="Delete from history">
              <i class="fa-solid fa-trash-can"></i>
            </button>
          </div>
        `;
        historyList.appendChild(card);
      });
    } catch (e) {
      console.error('Error fetching history:', e);
    }
  }

  window.deleteHistoryItem = async (id) => {
    try {
      await fetch(`/api/history/${id}`, { method: 'DELETE' });
      showToast('Removed item from history.', 'success');
      fetchHistory();
    } catch (e) {
      showToast('Failed to delete history item.', 'error');
    }
  };

  // Helper UI State Functions
  function setLoading(loading) {
    if (loading) {
      btnAnalyze.disabled = true;
      btnText.classList.add('hidden');
      spinner.classList.remove('hidden');
    } else {
      btnAnalyze.disabled = false;
      btnText.classList.remove('hidden');
      spinner.classList.add('hidden');
    }
  }

  function showError(title, message, needsCookies = false) {
    errorTitle.textContent = title;
    errorMessage.textContent = message;
    if (errorActions) {
      errorActions.classList.toggle('hidden', !needsCookies);
    }
    errorBanner.classList.remove('hidden');
    errorBanner.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }

  function hideError() {
    errorBanner.classList.add('hidden');
    if (errorActions) errorActions.classList.add('hidden');
  }

  function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    const icon = type === 'success' ? 'fa-circle-check' : 'fa-triangle-exclamation';
    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    toastContainer.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = '0';
      toast.style.transform = 'translateX(40px)';
      toast.style.transition = 'all 0.3s ease';
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }
});
