/**
 * Usage notice for the demo environment
 */

(function() {
    'use strict';

    const NOTICE_KEY = 'northstar_notice_acknowledged';

    if (localStorage.getItem(NOTICE_KEY)) {
        return;
    }

    function createNotice() {
        const sheet = document.createElement('div');
        sheet.id = 'app-notice';
        sheet.innerHTML = `
            <div class="app-notice-backdrop"></div>
            <div class="app-notice-sheet" role="dialog" aria-labelledby="notice-title">
                <div class="app-notice-handle" aria-hidden="true"></div>
                <div class="app-notice-content">
                    <div class="app-notice-header">
                        <div class="app-notice-icon">
                            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path>
                                <line x1="12" y1="9" x2="12" y2="13"></line>
                                <line x1="12" y1="17" x2="12.01" y2="17"></line>
                            </svg>
                        </div>
                        <h3 id="notice-title">Heads up</h3>
                        <button class="app-notice-close" aria-label="Close" onclick="dismissAppNotice()">
                            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"></line>
                                <line x1="6" y1="6" x2="18" y2="18"></line>
                            </svg>
                        </button>
                    </div>
                    <div class="app-notice-body">
                        <p>This demo is intended for practice and evaluation. Avoid entering real credentials or personal information.</p>
                    </div>
                    <div class="app-notice-actions">
                        <button id="notice-acknowledge" class="app-notice-btn app-notice-btn-primary">Got it</button>
                        <button onclick="dismissAppNotice()" class="app-notice-btn app-notice-btn-secondary">Remind me later</button>
                    </div>
                </div>
            </div>
        `;

        const style = document.createElement('style');
        style.textContent = `
            #app-notice {
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                z-index: 99999;
                pointer-events: none;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            }
            .app-notice-backdrop {
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.4);
                backdrop-filter: blur(2px);
                opacity: 0;
                transition: opacity 0.3s ease;
                pointer-events: auto;
            }
            .app-notice-sheet {
                position: absolute;
                bottom: 0;
                left: 0;
                right: 0;
                background: var(--bg, #1a1f2e);
                border-radius: 20px 20px 0 0;
                box-shadow: 0 -4px 24px rgba(0, 0, 0, 0.2);
                transform: translateY(100%);
                transition: transform 0.3s ease;
                pointer-events: auto;
                max-width: 600px;
                margin: 0 auto;
            }
            #app-notice.visible .app-notice-backdrop {
                opacity: 1;
            }
            #app-notice.visible .app-notice-sheet {
                transform: translateY(0);
            }
            .app-notice-handle {
                width: 40px;
                height: 4px;
                background: var(--border, rgba(255,255,255,0.2));
                border-radius: 2px;
                margin: 8px auto;
            }
            .app-notice-content {
                padding: 0 1.5rem 1.5rem;
            }
            .app-notice-header {
                display: flex;
                align-items: flex-start;
                gap: 1rem;
                margin-bottom: 1rem;
            }
            .app-notice-icon {
                flex-shrink: 0;
                width: 40px;
                height: 40px;
                background: rgba(0, 123, 255, 0.15);
                border-radius: 10px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            .app-notice-icon svg {
                width: 22px;
                height: 22px;
                color: #007BFF;
            }
            .app-notice-header h3 {
                flex: 1;
                margin: 0;
                font-size: 1rem;
                font-weight: 600;
                color: var(--text-1, #e0e6ed);
            }
            .app-notice-close {
                flex-shrink: 0;
                width: 28px;
                height: 28px;
                background: transparent;
                border: none;
                color: var(--text-3, rgba(255,255,255,0.5));
                cursor: pointer;
                border-radius: 6px;
                display: flex;
                align-items: center;
                justify-content: center;
                transition: background 0.2s;
            }
            .app-notice-close:hover {
                background: rgba(255,255,255,0.1);
            }
            .app-notice-body {
                color: var(--text-2, rgba(255,255,255,0.7));
                font-size: 0.875rem;
                line-height: 1.5;
            }
            .app-notice-body p {
                margin: 0 0 0.75rem;
            }
            .app-notice-actions {
                display: flex;
                gap: 0.75rem;
                margin-top: 1.25rem;
            }
            .app-notice-btn {
                flex: 1;
                padding: 0.75rem 1rem;
                font-size: 0.875rem;
                font-weight: 600;
                border-radius: 10px;
                cursor: pointer;
                transition: all 0.2s;
                border: none;
            }
            .app-notice-btn-primary {
                background: #007BFF;
                color: #fff;
            }
            .app-notice-btn-primary:hover {
                background: #0062CC;
            }
            .app-notice-btn-secondary {
                background: transparent;
                color: var(--text-2, rgba(255,255,255,0.7));
                border: 1px solid var(--border, rgba(255,255,255,0.15));
            }
            .app-notice-btn-secondary:hover {
                background: rgba(255,255,255,0.08);
            }
            @media (max-width: 600px) {
                .app-notice-sheet {
                    border-radius: 16px 16px 0 0;
                }
                .app-notice-content {
                    padding: 0 1rem 1rem;
                }
                .app-notice-actions {
                    flex-direction: column;
                }
            }
        `;

        document.head.appendChild(style);
        document.body.appendChild(sheet);

        requestAnimationFrame(() => {
            sheet.classList.add('visible');
        });

        document.getElementById('notice-acknowledge').addEventListener('click', function() {
            localStorage.setItem(NOTICE_KEY, 'true');
            dismissAppNotice();
        });
    }

    window.dismissAppNotice = function() {
        const sheet = document.getElementById('app-notice');
        if (!sheet) return;
        sheet.classList.remove('visible');
        setTimeout(() => {
            if (sheet.parentNode) {
                sheet.parentNode.removeChild(sheet);
            }
        }, 300);
    };

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', createNotice);
    } else {
        createNotice();
    }
})();
