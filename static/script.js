document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('extract-form');
    const urlInput = document.getElementById('target-url');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const spinner = submitBtn.querySelector('.spinner');
    const btnIcon = submitBtn.querySelector('.btn-icon');
    const pasteBtn = document.getElementById('paste-btn');
    const clearBtn = document.getElementById('clear-btn');

    const statusContainer = document.getElementById('status-container');
    const statusBox = document.getElementById('status-box');
    const statusIcon = document.getElementById('status-icon');
    const statusTitle = document.getElementById('status-title');
    const statusMessage = document.getElementById('status-message');

    const resultsSection = document.getElementById('results-section');
    const resultsCount = document.getElementById('results-count');
    const resultsSource = document.getElementById('results-source');
    const openAllBtn = document.getElementById('open-all-btn');
    const linksList = document.getElementById('links-list');
    const toast = document.getElementById('toast');

    let currentLinks = [];
    let toastTimeout = null;

    // Build the SaveTheVideo URL with URL-encoding
    function buildSaveTheVideoUrl(rawUrl) {
        return `https://www.savethevideo.com/home?url=${encodeURIComponent(rawUrl)}`;
    }

    // Toggle Clear button visibility based on input value
    urlInput.addEventListener('input', () => {
        if (urlInput.value.trim().length > 0) {
            clearBtn.classList.remove('hidden');
        } else {
            clearBtn.classList.add('hidden');
        }
    });

    // Clear input
    clearBtn.addEventListener('click', () => {
        urlInput.value = '';
        clearBtn.classList.add('hidden');
        urlInput.focus();
    });

    // Paste from clipboard
    pasteBtn.addEventListener('click', async () => {
        try {
            const text = await navigator.clipboard.readText();
            if (text) {
                urlInput.value = text.trim();
                clearBtn.classList.remove('hidden');
                urlInput.focus();
            }
        } catch (err) {
            showToast('Unable to read clipboard. Please paste manually.');
        }
    });

    // Handle Form Submit
    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const url = urlInput.value.trim();

        if (!url) {
            showStatus('error', 'URL Required', 'Please enter a target webpage URL.');
            return;
        }

        // Set Loading State
        setLoading(true);
        hideStatus();
        hideResults();

        try {
            const response = await fetch('/api/extract', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ url }),
            });

            const data = await response.json();

            if (!response.ok) {
                const errorMsg = data.detail || data.error || `Server responded with status ${response.status}`;
                showStatus('error', 'Extraction Failed', errorMsg);
                return;
            }

            if (data.success && data.links && data.links.length > 0) {
                currentLinks = data.links;
                displayResults(data.links, data.source);
            } else {
                showStatus('warning', 'No Links Found', data.error || 'No matching video source or iframe links were detected on this page.');
            }
        } catch (error) {
            showStatus('error', 'Network Error', error.message || 'Failed to reach the local backend server.');
        } finally {
            setLoading(false);
        }
    });

    // Open All Links in SaveTheVideo
    if (openAllBtn) {
        openAllBtn.addEventListener('click', () => {
            if (currentLinks.length === 0) return;
            currentLinks.forEach((link) => {
                const stvUrl = buildSaveTheVideoUrl(link);
                window.open(stvUrl, '_blank', 'noopener,noreferrer');
            });
        });
    }

    // Render results
    function displayResults(links, source) {
        linksList.innerHTML = '';
        resultsCount.textContent = `${links.length} Link${links.length > 1 ? 's' : ''} Found`;

        // Format source display
        if (source === 'iframe_selector') {
            resultsSource.textContent = 'Source: DOM iframe (#pembed)';
            resultsSource.style.background = 'rgba(16, 185, 129, 0.15)';
            resultsSource.style.color = '#6ee7b7';
            resultsSource.style.borderColor = 'rgba(16, 185, 129, 0.3)';
        } else if (source === 'dailymotion_fallback') {
            resultsSource.textContent = 'Source: Dailymotion Regex Fallback';
            resultsSource.style.background = 'rgba(99, 102, 241, 0.15)';
            resultsSource.style.color = '#a5b4fc';
            resultsSource.style.borderColor = 'rgba(99, 102, 241, 0.3)';
        } else {
            resultsSource.textContent = `Source: ${source || 'Unknown'}`;
        }

        // Show/hide Open All button
        if (openAllBtn) {
            if (links.length > 1) {
                openAllBtn.classList.remove('hidden');
            } else {
                openAllBtn.classList.add('hidden');
            }
        }

        links.forEach((link, idx) => {
            const saveTheVideoUrl = buildSaveTheVideoUrl(link);
            const card = document.createElement('div');
            card.className = 'link-card';

            card.innerHTML = `
                <div class="link-info">
                    <span class="link-index">#${idx + 1}</span>
                    <span class="link-url" title="${escapeHtml(link)}">${escapeHtml(link)}</span>
                </div>
                <div class="link-buttons">
                    <a href="${escapeHtml(saveTheVideoUrl)}" target="_blank" rel="noopener noreferrer" class="link-action-btn primary-action">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
                            <polyline points="15 3 21 3 21 9"></polyline>
                            <line x1="10" y1="14" x2="21" y2="3"></line>
                        </svg>
                        <span>Open in SaveTheVideo</span>
                    </a>
                </div>
            `;

            linksList.appendChild(card);
        });

        resultsSection.classList.remove('hidden');
    }

    // Set UI loading state
    function setLoading(isLoading) {
        if (isLoading) {
            submitBtn.disabled = true;
            btnText.textContent = 'Extracting...';
            spinner.classList.remove('hidden');
            btnIcon.classList.add('hidden');
        } else {
            submitBtn.disabled = false;
            btnText.textContent = 'Extract Links';
            spinner.classList.add('hidden');
            btnIcon.classList.remove('hidden');
        }
    }

    // Status alerts
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
            iconSvg = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>`;
        }
        statusIcon.innerHTML = iconSvg;
        statusContainer.classList.remove('hidden');
    }

    function hideStatus() {
        statusContainer.classList.add('hidden');
    }

    function hideResults() {
        resultsSection.classList.add('hidden');
        linksList.innerHTML = '';
        currentLinks = [];
    }

    // Toast message
    function showToast(message) {
        if (toastTimeout) clearTimeout(toastTimeout);
        toast.textContent = message;
        toast.classList.remove('hidden');
        toastTimeout = setTimeout(() => {
            toast.classList.add('hidden');
        }, 2500);
    }

    // Helper: Escape HTML
    function escapeHtml(str) {
        return str
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
});
