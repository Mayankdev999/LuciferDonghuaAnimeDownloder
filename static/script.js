document.addEventListener('DOMContentLoaded', () => {
    // --- State & DOM References ---
    const tabs = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');
    const seriesView = document.getElementById('series-view');
    const backToListBtn = document.getElementById('back-to-list-btn');

    // Status & Toast
    const statusContainer = document.getElementById('status-container');
    const statusBox = document.getElementById('status-box');
    const statusIcon = document.getElementById('status-icon');
    const statusTitle = document.getElementById('status-title');
    const statusMessage = document.getElementById('status-message');
    const toast = document.getElementById('toast');
    let toastTimeout = null;

    // Bookmarks Tab
    const bookmarksGrid = document.getElementById('bookmarks-grid');
    const bookmarksEmpty = document.getElementById('bookmarks-empty');
    const bookmarksCount = document.getElementById('bookmarks-count');

    // Search Tab
    const searchForm = document.getElementById('search-form');
    const searchInput = document.getElementById('search-input');
    const searchClearBtn = document.getElementById('search-clear-btn');
    const searchSubmitBtn = document.getElementById('search-submit-btn');
    const searchResultsWrapper = document.getElementById('search-results-wrapper');
    const searchGrid = document.getElementById('search-grid');
    const searchCount = document.getElementById('search-count');
    const quickPickChips = document.querySelectorAll('.quick-pick-chip');

    // Direct URL Tab
    const extractForm = document.getElementById('extract-form');
    const targetUrlInput = document.getElementById('target-url');
    const extractSubmitBtn = document.getElementById('submit-btn');
    const pasteBtn = document.getElementById('paste-btn');
    const clearBtn = document.getElementById('clear-btn');
    const directResultsSection = document.getElementById('direct-results-section');
    const directResultsCount = document.getElementById('direct-results-count');
    const directResultsSource = document.getElementById('direct-results-source');
    const directOpenAllBtn = document.getElementById('direct-open-all-btn');
    const directLinksList = document.getElementById('direct-links-list');

    // Series View Elements
    const seriesPoster = document.getElementById('series-poster');
    const seriesTitle = document.getElementById('series-title');
    const seriesBookmarkBtn = document.getElementById('series-bookmark-btn');
    const seriesBookmarkText = document.getElementById('series-bookmark-text');
    const seriesMetaChips = document.getElementById('series-meta-chips');
    const seriesSynopsis = document.getElementById('series-synopsis');
    const synopsisToggleBtn = document.getElementById('synopsis-toggle-btn');
    const seriesProgressBox = document.getElementById('series-progress-box');
    const seriesProgressText = document.getElementById('series-progress-text');
    const episodesTotalCount = document.getElementById('episodes-total-count');
    const episodeFilterInput = document.getElementById('episode-filter-input');
    const sortOrderBtn = document.getElementById('sort-order-btn');
    const sortBtnText = document.getElementById('sort-btn-text');
    const episodesGrid = document.getElementById('episodes-grid');

    // Batch Panel
    const batchDownloadModalBtn = document.getElementById('batch-download-modal-btn');
    const batchPanel = document.getElementById('batch-panel');
    const batchCloseBtn = document.getElementById('batch-close-btn');
    const batchFromInput = document.getElementById('batch-from-input');
    const batchToInput = document.getElementById('batch-to-input');
    const batchExecuteBtn = document.getElementById('batch-execute-btn');
    const batchNext5Btn = document.getElementById('batch-next-5-btn');
    const batchStatus = document.getElementById('batch-status');

    // Episode Action Modal
    const episodeModal = document.getElementById('episode-modal');
    const modalCloseBtn = document.getElementById('modal-close-btn');
    const modalEpisodeTitle = document.getElementById('modal-episode-title');
    const modalSeriesName = document.getElementById('modal-series-name');
    const modalLoading = document.getElementById('modal-loading');
    const modalSuccess = document.getElementById('modal-success');
    const modalFailed = document.getElementById('modal-failed');
    const modalErrorMsg = document.getElementById('modal-error-msg');
    const modalSourceBadge = document.getElementById('modal-source-badge');
    const modalStreamUrl = document.getElementById('modal-stream-url');
    const modalOpenStvBtn = document.getElementById('modal-open-stv-btn');
    const modalCopyLinkBtn = document.getElementById('modal-copy-link-btn');
    const modalCopyLinkText = document.getElementById('modal-copy-link-text');
    const modalOpenOriginalBtn = document.getElementById('modal-open-original-btn');

    // Memory variables
    let currentSeriesData = null;
    let currentEpisodes = [];
    let isDescending = true; // Default: latest first
    let previousActiveTab = 'bookmarks-tab';
    let directLinks = [];
    let currentModalStreamUrl = '';

    // LocalStorage Keys
    const LS_BOOKMARKS_KEY = 'theanimelink_bookmarks';
    const LS_PROGRESS_KEY = 'theanimelink_progress_v2';

    // ----------------------------------------------------------------
    // 1. LOCALSTORAGE MANAGERS (Per-Anime Progress & Bookmarks)
    // ----------------------------------------------------------------

    function getBookmarks() {
        try {
            return JSON.parse(localStorage.getItem(LS_BOOKMARKS_KEY)) || [];
        } catch (e) {
            return [];
        }
    }

    function isBookmarked(url) {
        const bookmarks = getBookmarks();
        return bookmarks.some(b => b.url === url);
    }

    function toggleBookmark(anime) {
        let bookmarks = getBookmarks();
        const index = bookmarks.findIndex(b => b.url === anime.url);

        if (index > -1) {
            bookmarks.splice(index, 1);
            showToast(`Removed "${anime.title}" from Bookmarks`);
        } else {
            bookmarks.unshift({
                url: anime.url,
                title: anime.title,
                poster: anime.poster,
                status: anime.status || '',
                type: anime.type || ''
            });
            showToast(`⭐ Bookmarked "${anime.title}"`);
        }

        localStorage.setItem(LS_BOOKMARKS_KEY, JSON.stringify(bookmarks));
        updateBookmarksCountBadge();
        renderBookmarksTab();
        updateSeriesBookmarkButton();
    }

    function getAllProgress() {
        try {
            return JSON.parse(localStorage.getItem(LS_PROGRESS_KEY)) || {};
        } catch (e) {
            return {};
        }
    }

    function getAnimeProgress(animeUrl) {
        const progress = getAllProgress();
        return progress[animeUrl] || null;
    }

    // Records an episode download in per-anime history
    function setAnimeProgress(animeUrl, episode) {
        const progress = getAllProgress();
        const existing = progress[animeUrl] || { downloaded_eps: [] };

        const downloadedSet = new Set(existing.downloaded_eps || []);
        if (episode.num) downloadedSet.add(episode.num);

        progress[animeUrl] = {
            downloaded_eps: Array.from(downloadedSet),
            last_ep_num: episode.num,
            last_ep_title: episode.title || '',
            last_ep_url: episode.url,
            timestamp: Date.now()
        };

        localStorage.setItem(LS_PROGRESS_KEY, JSON.stringify(progress));

        updateSeriesProgressBadge();
        renderBookmarksTab();
    }

    function isEpisodeDownloaded(animeUrl, epNum) {
        const progress = getAnimeProgress(animeUrl);
        if (!progress || !progress.downloaded_eps) return false;
        return progress.downloaded_eps.includes(epNum);
    }

    function updateBookmarksCountBadge() {
        const bookmarks = getBookmarks();
        if (bookmarks.length > 0) {
            bookmarksCount.textContent = bookmarks.length;
            bookmarksCount.classList.remove('hidden');
        } else {
            bookmarksCount.classList.add('hidden');
        }
    }

    // ----------------------------------------------------------------
    // 2. TAB SWITCHING LOGIC
    // ----------------------------------------------------------------

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const targetTabId = tab.getAttribute('data-tab');
            switchTab(targetTabId);
        });
    });

    document.querySelectorAll('.switch-to-search-btn').forEach(btn => {
        btn.addEventListener('click', () => switchTab('search-tab'));
    });

    function switchTab(tabId) {
        seriesView.classList.add('hidden');

        tabs.forEach(t => t.classList.toggle('active', t.getAttribute('data-tab') === tabId));
        tabContents.forEach(c => {
            if (c.id === tabId) {
                c.classList.remove('hidden');
                c.classList.add('active');
            } else {
                c.classList.add('hidden');
                c.classList.remove('active');
            }
        });

        previousActiveTab = tabId;
        hideStatus();

        if (tabId === 'bookmarks-tab') {
            renderBookmarksTab();
        }
    }

    backToListBtn.addEventListener('click', () => {
        seriesView.classList.add('hidden');
        switchTab(previousActiveTab);
        if (window.location.hash) {
            history.pushState("", document.title, window.location.pathname + window.location.search);
        }
    });

    // Native browser Back button support
    window.addEventListener('popstate', (e) => {
        if (!seriesView.classList.contains('hidden')) {
            seriesView.classList.add('hidden');
            switchTab(previousActiveTab);
        }
    });

    // ----------------------------------------------------------------
    // 3. BOOKMARKS TAB RENDERING
    // ----------------------------------------------------------------

    function renderBookmarksTab() {
        const bookmarks = getBookmarks();
        bookmarksGrid.innerHTML = '';

        if (bookmarks.length === 0) {
            bookmarksEmpty.classList.remove('hidden');
            bookmarksGrid.classList.add('hidden');
            return;
        }

        bookmarksEmpty.classList.add('hidden');
        bookmarksGrid.classList.remove('hidden');

        bookmarks.forEach(anime => {
            const card = createAnimeCard(anime, true);
            bookmarksGrid.appendChild(card);
        });
    }

    // ----------------------------------------------------------------
    // 4. ANIME CARD BUILDER (Generic for Search & Bookmarks)
    // ----------------------------------------------------------------

    function createAnimeCard(anime) {
        const card = document.createElement('div');
        card.className = 'anime-card';

        const progress = getAnimeProgress(anime.url);
        const bookmarked = isBookmarked(anime.url);

        let progressHtml = '';
        if (progress && progress.last_ep_num) {
            progressHtml = `
                <div class="card-progress-pill" title="Last downloaded episode">
                    <span>✓ Ep ${escapeHtml(progress.last_ep_num)}</span>
                </div>
            `;
        }

        let statusBadge = '';
        if (anime.status) {
            statusBadge = `<span class="card-badge status-badge">${escapeHtml(anime.status)}</span>`;
        }

        const fallbackPosterSvg = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='100' height='140'><rect fill='%23171c2a' width='100' height='140'/><text fill='%2364748b' x='50%' y='50%' dominant-baseline='middle' text-anchor='middle' font-size='12'>No Poster</text></svg>";

        card.innerHTML = `
            <div class="anime-poster-wrapper">
                <img src="${escapeHtml(anime.poster || fallbackPosterSvg)}" alt="${escapeHtml(anime.title)}" loading="lazy" onerror="this.src='${fallbackPosterSvg}'">
                ${statusBadge}
                <button type="button" class="card-bookmark-btn ${bookmarked ? 'bookmarked' : ''}" title="${bookmarked ? 'Remove Bookmark' : 'Bookmark Series'}">
                    <svg width="15" height="15" viewBox="0 0 24 24" fill="${bookmarked ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
                        <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon>
                    </svg>
                </button>
                ${progressHtml}
            </div>
            <div class="anime-card-content">
                <h4 class="anime-card-title" title="${escapeHtml(anime.title)}">${escapeHtml(anime.title)}</h4>
            </div>
        `;

        card.addEventListener('click', (e) => {
            if (e.target.closest('.card-bookmark-btn')) return;
            openSeries(anime.url, anime);
        });

        const bBtn = card.querySelector('.card-bookmark-btn');
        bBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            toggleBookmark(anime);
        });

        return card;
    }

    // ----------------------------------------------------------------
    // 5. SEARCH LOGIC & QUICK PICKS
    // ----------------------------------------------------------------

    // Quick pick chips listener (1-tap search)
    quickPickChips.forEach(chip => {
        chip.addEventListener('click', () => {
            searchInput.value = chip.textContent.trim();
            searchClearBtn.classList.remove('hidden');
            searchForm.requestSubmit();
        });
    });

    searchInput.addEventListener('input', () => {
        searchClearBtn.classList.toggle('hidden', searchInput.value.trim().length === 0);
    });

    searchClearBtn.addEventListener('click', () => {
        searchInput.value = '';
        searchClearBtn.classList.add('hidden');
        searchInput.focus();
    });

    searchForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (!query) return;

        setSearchLoading(true);
        hideStatus();
        searchResultsWrapper.classList.add('hidden');
        searchGrid.innerHTML = '';

        try {
            const res = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
            const data = await res.json();

            if (!res.ok || !data.success) {
                showStatus('error', 'Search Error', data.error || 'Failed to fetch search results.');
                return;
            }

            if (data.results && data.results.length > 0) {
                searchCount.textContent = `${data.results.length} Results Found for "${query}"`;
                data.results.forEach(anime => {
                    const card = createAnimeCard(anime);
                    searchGrid.appendChild(card);
                });
                searchResultsWrapper.classList.remove('hidden');
            } else {
                showStatus('warning', 'No Results', `No anime series found matching "${query}".`);
            }
        } catch (err) {
            showStatus('error', 'Network Error', err.message || 'Failed to connect to backend.');
        } finally {
            setSearchLoading(false);
        }
    });

    function setSearchLoading(isLoading) {
        searchSubmitBtn.disabled = isLoading;
        searchSubmitBtn.querySelector('.btn-text').textContent = isLoading ? 'Searching...' : 'Search';
        searchSubmitBtn.querySelector('.spinner').classList.toggle('hidden', !isLoading);
    }

    // ----------------------------------------------------------------
    // 6. SERIES & EPISODES VIEWER
    // ----------------------------------------------------------------

    async function openSeries(seriesUrl, fallbackMeta = null) {
        tabContents.forEach(c => c.classList.add('hidden'));
        seriesView.classList.remove('hidden');
        hideStatus();
        window.scrollTo({ top: 0, behavior: 'smooth' });

        // Update browser history state
        history.pushState({ view: 'series', url: seriesUrl }, '', '#series');

        // Placeholder loading state
        seriesTitle.textContent = fallbackMeta ? fallbackMeta.title : 'Loading Series...';
        seriesPoster.src = fallbackMeta ? fallbackMeta.poster : '';
        seriesMetaChips.innerHTML = '';
        seriesSynopsis.textContent = 'Fetching complete episode list from LuciferDonghua...';
        synopsisToggleBtn.classList.add('hidden');
        episodesGrid.innerHTML = '<div style="grid-column: 1/-1; padding: 30px; color: var(--text-muted); text-align: center;">Loading episodes...</div>';
        episodesTotalCount.textContent = '...';
        batchPanel.classList.add('hidden');
        episodeFilterInput.value = '';

        try {
            const res = await fetch(`/api/series?url=${encodeURIComponent(seriesUrl)}`);
            const data = await res.json();

            if (!res.ok || !data.success) {
                showStatus('error', 'Failed to Load Series', data.error || 'Could not parse episodes.');
                return;
            }

            currentSeriesData = data;
            currentEpisodes = data.episodes || [];
            isDescending = true;
            sortBtnText.textContent = 'Newest First';
            sortOrderBtn.classList.remove('ascending');

            seriesTitle.textContent = data.title;
            if (data.poster) seriesPoster.src = data.poster;
            
            // Synopsis with Read more toggle
            const synopsisText = data.synopsis || 'No synopsis available.';
            seriesSynopsis.textContent = synopsisText;
            if (synopsisText.length > 160) {
                seriesSynopsis.classList.add('collapsed');
                synopsisToggleBtn.textContent = 'Read more ▼';
                synopsisToggleBtn.classList.remove('hidden');
            } else {
                seriesSynopsis.classList.remove('collapsed');
                synopsisToggleBtn.classList.add('hidden');
            }

            // Meta chips
            let chipsHtml = '';
            if (data.status) {
                const statusClass = data.status.toLowerCase().includes('ongoing') ? 'status-ongoing' : 'status-completed';
                chipsHtml += `<span class="meta-chip ${statusClass}">${escapeHtml(data.status)}</span>`;
            }
            if (data.studio) {
                chipsHtml += `<span class="meta-chip">Studio: ${escapeHtml(data.studio)}</span>`;
            }
            if (data.genres && data.genres.length > 0) {
                data.genres.slice(0, 4).forEach(g => {
                    chipsHtml += `<span class="meta-chip">${escapeHtml(g)}</span>`;
                });
            }
            seriesMetaChips.innerHTML = chipsHtml;

            updateSeriesBookmarkButton();
            updateSeriesProgressBadge();
            renderEpisodeGrid();

        } catch (err) {
            showStatus('error', 'Network Error', err.message || 'Failed to fetch series.');
        }
    }

    // Synopsis expand / collapse
    synopsisToggleBtn.addEventListener('click', () => {
        const isCollapsed = seriesSynopsis.classList.contains('collapsed');
        if (isCollapsed) {
            seriesSynopsis.classList.remove('collapsed');
            synopsisToggleBtn.textContent = 'Read less ▲';
        } else {
            seriesSynopsis.classList.add('collapsed');
            synopsisToggleBtn.textContent = 'Read more ▼';
        }
    });

    function updateSeriesBookmarkButton() {
        if (!currentSeriesData) return;
        const bookmarked = isBookmarked(currentSeriesData.url);
        seriesBookmarkBtn.classList.toggle('bookmarked', bookmarked);
        seriesBookmarkText.textContent = bookmarked ? 'Bookmarked ⭐' : 'Bookmark Series';
    }

    seriesBookmarkBtn.addEventListener('click', () => {
        if (!currentSeriesData) return;
        toggleBookmark(currentSeriesData);
    });

    function updateSeriesProgressBadge() {
        if (!currentSeriesData) return;
        const progress = getAnimeProgress(currentSeriesData.url);
        if (progress && progress.last_ep_num) {
            const count = progress.downloaded_eps ? progress.downloaded_eps.length : 1;
            seriesProgressText.textContent = `Ep ${progress.last_ep_num} (Total grabbed: ${count})`;
            seriesProgressBox.classList.remove('hidden');
        } else {
            seriesProgressBox.classList.add('hidden');
        }
    }

    // Sort order button toggle
    sortOrderBtn.addEventListener('click', () => {
        isDescending = !isDescending;
        sortBtnText.textContent = isDescending ? 'Newest First' : 'Oldest First';
        sortOrderBtn.classList.toggle('ascending', !isDescending);
        renderEpisodeGrid();
    });

    // Episode filter input
    episodeFilterInput.addEventListener('input', () => {
        renderEpisodeGrid();
    });

    function renderEpisodeGrid() {
        episodesGrid.innerHTML = '';
        if (!currentEpisodes || currentEpisodes.length === 0) {
            episodesGrid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-dim); padding: 20px;">No episodes found.</div>';
            episodesTotalCount.textContent = '0';
            return;
        }

        let displayList = isDescending ? [...currentEpisodes] : [...currentEpisodes].reverse();

        const filterVal = episodeFilterInput.value.trim().toLowerCase();
        if (filterVal) {
            displayList = displayList.filter(ep => {
                const numMatch = ep.num && ep.num.toLowerCase().includes(filterVal);
                const titleMatch = ep.title && ep.title.toLowerCase().includes(filterVal);
                return numMatch || titleMatch;
            });
        }

        if (filterVal) {
            episodesTotalCount.textContent = `${displayList.length} of ${currentEpisodes.length}`;
        } else {
            episodesTotalCount.textContent = currentEpisodes.length;
        }

        if (displayList.length === 0) {
            episodesGrid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-dim); padding: 24px;">No episodes match "${escapeHtml(filterVal)}".</div>`;
            return;
        }

        const progress = getAnimeProgress(currentSeriesData.url);
        const lastDownloadedEpNum = progress ? progress.last_ep_num : null;

        displayList.forEach(ep => {
            const epBtn = document.createElement('button');
            epBtn.type = 'button';
            epBtn.className = 'ep-btn';

            // Clean hover tooltip
            const releaseInfo = ep.date ? ` (Released: ${ep.date})` : '';
            epBtn.title = `Episode ${ep.num}${releaseInfo}`;

            // Check if downloaded or last downloaded
            const isDownloaded = isEpisodeDownloaded(currentSeriesData.url, ep.num);
            const isLast = (lastDownloadedEpNum && ep.num === lastDownloadedEpNum);

            if (isLast) {
                epBtn.classList.add('last-downloaded');
            } else if (isDownloaded) {
                epBtn.classList.add('downloaded');
            }

            epBtn.innerHTML = `<span class="ep-num">Ep ${escapeHtml(ep.num || '?')}</span>`;
            epBtn.addEventListener('click', () => openEpisodeActionModal(ep));
            episodesGrid.appendChild(epBtn);
        });
    }

    // ----------------------------------------------------------------
    // 7. EPISODE ACTION MODAL & STREAM EXTRACTION
    // ----------------------------------------------------------------

    async function openEpisodeActionModal(episode) {
        if (!episode || !episode.url) return;

        modalEpisodeTitle.textContent = `Episode ${episode.num}`;
        modalSeriesName.textContent = currentSeriesData ? currentSeriesData.title : '';
        modalOpenOriginalBtn.href = episode.url;

        // Reset modal state
        modalLoading.classList.remove('hidden');
        modalSuccess.classList.add('hidden');
        modalFailed.classList.add('hidden');
        modalCopyLinkText.textContent = 'Copy Direct Stream URL';
        currentModalStreamUrl = '';

        episodeModal.classList.remove('hidden');

        try {
            const res = await fetch('/api/extract', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url: episode.url })
            });
            const data = await res.json();

            modalLoading.classList.add('hidden');

            if (res.ok && data.success && data.links && data.links.length > 0) {
                // Priority #1 stream link
                currentModalStreamUrl = data.links[0];
                const saveTheVideoUrl = `https://www.savethevideo.com/home?url=${encodeURIComponent(currentModalStreamUrl)}`;

                modalSourceBadge.textContent = data.source === 'iframe_selector' ? 'DOM iframe Player' : 'Dailymotion Player Embed';
                modalStreamUrl.textContent = currentModalStreamUrl;
                modalOpenStvBtn.href = saveTheVideoUrl;

                modalSuccess.classList.remove('hidden');

                // Mark episode as downloaded in individual history
                if (currentSeriesData) {
                    setAnimeProgress(currentSeriesData.url, episode);
                    renderEpisodeGrid();
                }
            } else {
                modalErrorMsg.textContent = data.error || 'No direct video stream found on this episode page. You can still watch it on LuciferDonghua below.';
                modalFailed.classList.remove('hidden');
            }
        } catch (err) {
            modalLoading.classList.add('hidden');
            modalErrorMsg.textContent = 'Network error while extracting video link. Please try opening on LuciferDonghua.';
            modalFailed.classList.remove('hidden');
        }
    }

    // Copy stream link inside modal
    modalCopyLinkBtn.addEventListener('click', async () => {
        if (!currentModalStreamUrl) return;
        const success = await copyToClipboard(currentModalStreamUrl);
        if (success) {
            modalCopyLinkText.textContent = '✓ Copied Stream URL!';
            showToast('Stream URL copied to clipboard');
            setTimeout(() => {
                modalCopyLinkText.textContent = 'Copy Direct Stream URL';
            }, 2200);
        }
    });

    // Close modal handlers
    modalCloseBtn.addEventListener('click', () => {
        episodeModal.classList.add('hidden');
    });

    episodeModal.addEventListener('click', (e) => {
        if (e.target === episodeModal) {
            episodeModal.classList.add('hidden');
        }
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && !episodeModal.classList.contains('hidden')) {
            episodeModal.classList.add('hidden');
        }
    });

    // ----------------------------------------------------------------
    // 8. BATCH RANGE DOWNLOADER
    // ----------------------------------------------------------------

    batchDownloadModalBtn.addEventListener('click', () => {
        batchPanel.classList.toggle('hidden');
    });

    batchCloseBtn.addEventListener('click', () => {
        batchPanel.classList.add('hidden');
    });

    function parseEpNumInt(ep) {
        if (!ep || !ep.num) return null;
        const match = ep.num.match(/\d+/);
        return match ? parseInt(match[0], 10) : null;
    }

    // Next 5 Unwatched
    batchNext5Btn.addEventListener('click', () => {
        if (!currentEpisodes || currentEpisodes.length === 0) return;

        const progress = getAnimeProgress(currentSeriesData.url);
        let startEp = 1;

        if (progress && progress.last_ep_num) {
            const parsedLast = parseInt(progress.last_ep_num.match(/\d+/)?.[0] || '0', 10);
            if (parsedLast > 0) startEp = parsedLast + 1;
        }

        batchFromInput.value = startEp;
        batchToInput.value = startEp + 4;
        showBatchStatus(`Selected Ep ${startEp} to ${startEp + 4}. Click "Open Range" to process.`);
    });

    // Execute Batch Range
    batchExecuteBtn.addEventListener('click', async () => {
        const fromNum = parseInt(batchFromInput.value, 10);
        const toNum = parseInt(batchToInput.value, 10);

        if (isNaN(fromNum) || isNaN(toNum) || fromNum > toNum) {
            showBatchStatus('Please enter a valid From and To episode range.', true);
            return;
        }

        const episodesInRange = currentEpisodes.filter(ep => {
            const n = parseEpNumInt(ep);
            return n !== null && n >= fromNum && n <= toNum;
        });

        episodesInRange.sort((a, b) => parseEpNumInt(a) - parseEpNumInt(b));

        if (episodesInRange.length === 0) {
            showBatchStatus(`No episodes found between #${fromNum} and #${toNum}.`, true);
            return;
        }

        showBatchStatus(`Processing ${episodesInRange.length} episodes sequentially...`);
        batchExecuteBtn.disabled = true;

        for (let i = 0; i < episodesInRange.length; i++) {
            const ep = episodesInRange[i];
            showBatchStatus(`Extracting Ep ${ep.num} (${i + 1}/${episodesInRange.length})...`);
            
            try {
                const res = await fetch('/api/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: ep.url })
                });
                const data = await res.json();
                if (res.ok && data.success && data.links && data.links.length > 0) {
                    const streamLink = data.links[0];
                    const saveTheVideoUrl = `https://www.savethevideo.com/home?url=${encodeURIComponent(streamLink)}`;
                    window.open(saveTheVideoUrl, '_blank', 'noopener,noreferrer');
                    setAnimeProgress(currentSeriesData.url, ep);
                }
            } catch (err) {
                console.error(err);
            }
            await new Promise(r => setTimeout(r, 1200));
        }

        showBatchStatus(`✓ Done! Opened SaveTheVideo tabs for requested range.`);
        batchExecuteBtn.disabled = false;
        renderEpisodeGrid();
    });

    function showBatchStatus(msg, isError = false) {
        batchStatus.textContent = msg;
        batchStatus.style.color = isError ? '#fca5a5' : '#a7f3d0';
        batchStatus.classList.remove('hidden');
    }

    // ----------------------------------------------------------------
    // 9. DIRECT URL EXTRACTOR
    // ----------------------------------------------------------------

    targetUrlInput.addEventListener('input', () => {
        clearBtn.classList.toggle('hidden', targetUrlInput.value.trim().length === 0);
    });

    clearBtn.addEventListener('click', () => {
        targetUrlInput.value = '';
        clearBtn.classList.add('hidden');
        targetUrlInput.focus();
    });

    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                targetUrlInput.value = text.trim();
                clearBtn.classList.remove('hidden');
                targetUrlInput.focus();
            }
        } catch (err) {
            showToast('Unable to read clipboard. Please paste manually.');
        }
    });

    extractForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = targetUrlInput.value.trim();
        if (!url) return;

        setDirectLoading(true);
        hideStatus();
        directResultsSection.classList.add('hidden');
        directLinksList.innerHTML = '';
        directLinks = [];

        try {
            const response = await fetch('/api/extract', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ url })
            });
            const data = await response.json();

            if (!response.ok || !data.success) {
                showStatus('error', 'Extraction Failed', data.error || 'No video link detected.');
                return;
            }

            if (data.links && data.links.length > 0) {
                directLinks = data.links;
                displayDirectResults(data.links, data.source);
            } else {
                showStatus('warning', 'No Links', data.error || 'No matching links found.');
            }
        } catch (err) {
            showStatus('error', 'Network Error', err.message || 'Connection failed.');
        } finally {
            setDirectLoading(false);
        }
    });

    function setDirectLoading(isLoading) {
        extractSubmitBtn.disabled = isLoading;
        extractSubmitBtn.querySelector('.btn-text').textContent = isLoading ? 'Extracting...' : 'Extract Links';
        extractSubmitBtn.querySelector('.spinner').classList.toggle('hidden', !isLoading);
    }

    function displayDirectResults(links, source) {
        directLinksList.innerHTML = '';
        directResultsCount.textContent = `${links.length} Link${links.length > 1 ? 's' : ''} Found`;
        directResultsSource.textContent = `Source: ${source === 'iframe_selector' ? 'DOM iframe (#pembed)' : 'Dailymotion Fallback'}`;

        if (directOpenAllBtn) {
            directOpenAllBtn.classList.toggle('hidden', links.length <= 1);
        }

        links.forEach((link, idx) => {
            const saveTheVideoUrl = `https://www.savethevideo.com/home?url=${encodeURIComponent(link)}`;
            const card = document.createElement('div');
            card.className = 'link-card';

            card.innerHTML = `
                <div class="link-info">
                    <span class="link-index">#${idx + 1}</span>
                    <span class="link-url" title="${escapeHtml(link)}">${escapeHtml(link)}</span>
                </div>
                <div class="link-actions-group">
                    <a href="${escapeHtml(saveTheVideoUrl)}" target="_blank" rel="noopener noreferrer" class="action-btn primary-action">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path><polyline points="15 3 21 3 21 9"></polyline><line x1="10" y1="14" x2="21" y2="3"></line></svg>
                        <span>Open in SaveTheVideo</span>
                    </a>
                    <button type="button" class="action-btn secondary copy-raw-btn" data-url="${escapeHtml(link)}">
                        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg>
                        <span>Copy URL</span>
                    </button>
                </div>
            `;

            const copyBtn = card.querySelector('.copy-raw-btn');
            copyBtn.addEventListener('click', async () => {
                const u = copyBtn.getAttribute('data-url');
                const ok = await copyToClipboard(u);
                if (ok) {
                    copyBtn.innerHTML = `<span>✓ Copied!</span>`;
                    showToast('Copied raw stream URL');
                    setTimeout(() => {
                        copyBtn.innerHTML = `<svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path></svg><span>Copy URL</span>`;
                    }, 2000);
                }
            });

            directLinksList.appendChild(card);
        });

        directResultsSection.classList.remove('hidden');
    }

    if (directOpenAllBtn) {
        directOpenAllBtn.addEventListener('click', () => {
            directLinks.forEach(link => {
                const stvUrl = `https://www.savethevideo.com/home?url=${encodeURIComponent(link)}`;
                window.open(stvUrl, '_blank', 'noopener,noreferrer');
            });
        });
    }

    // ----------------------------------------------------------------
    // 10. STATUS, TOAST & UTILS
    // ----------------------------------------------------------------

    function showStatus(type, title, message) {
        statusBox.className = `status-box ${type}`;
        statusTitle.textContent = title;
        statusMessage.textContent = message;

        let iconSvg = '';
        if (type === 'error') {
            iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
        } else if (type === 'warning') {
            iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="m21.73 18-8-14a2 2 0 0 0-3.48 0l-8 14A2 2 0 0 0 4 21h16a2 2 0 0 0 1.73-3Z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`;
        } else {
            iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>`;
        }
        statusIcon.innerHTML = iconSvg;
        statusContainer.classList.remove('hidden');
    }

    function hideStatus() {
        statusContainer.classList.add('hidden');
    }

    function showToast(message) {
        if (toastTimeout) clearTimeout(toastTimeout);
        toast.textContent = message;
        toast.classList.remove('hidden');
        toastTimeout = setTimeout(() => {
            toast.classList.add('hidden');
        }, 2800);
    }

    async function copyToClipboard(text) {
        try {
            if (navigator.clipboard && window.isSecureContext) {
                await navigator.clipboard.writeText(text);
                return true;
            } else {
                const textArea = document.createElement('textarea');
                textArea.value = text;
                textArea.style.position = 'fixed';
                textArea.style.left = '-999999px';
                textArea.style.top = '-999999px';
                document.body.appendChild(textArea);
                textArea.focus();
                textArea.select();
                const successful = document.execCommand('copy');
                textArea.remove();
                return successful;
            }
        } catch (err) {
            return false;
        }
    }

    function escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    // ----------------------------------------------------------------
    // 11. INITIALIZATION
    // ----------------------------------------------------------------
    updateBookmarksCountBadge();
    const existingBookmarks = getBookmarks();
    if (existingBookmarks.length > 0) {
        switchTab('bookmarks-tab');
    } else {
        switchTab('search-tab');
    }
});
