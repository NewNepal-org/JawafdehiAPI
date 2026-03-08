(function() {
    function init() {
        // Wait for libraries to load
        if (typeof NepaliFunctions === 'undefined') {
            setTimeout(init, 100);
            return;
        }

        // Check if NepaliDatePicker is available via prototype
        if (typeof HTMLElement.prototype.nepaliDatePicker === 'undefined') {
            console.error('NepaliDatePicker not loaded');
            setTimeout(init, 100);
            return;
        }

        const startAd = document.getElementById('id_case_start_date');
        const startBs = document.getElementById('id_start_date_bs');
        const endAd = document.getElementById('id_case_end_date');
        const endBs = document.getElementById('id_end_date_bs');

        if (!startAd || !startBs || !endAd || !endBs) {
            setTimeout(init, 200);
            return;
        }

        // Temporarily remove readonly to allow datepicker initialization
        startBs.removeAttribute('readonly');
        endBs.removeAttribute('readonly');

        // Initialize Nepali datepicker on BS fields
        startBs.nepaliDatePicker({
            dateFormat: 'YYYY-MM-DD',
            language: 'english',
            mode: 'light',
            container: 'body',
            onSelect: function(dateObj) {
                if (dateObj && dateObj.value) {
                    const bsDate = NepaliFunctions.ConvertToDateObject(dateObj.value, 'YYYY-MM-DD');
                    const adDate = NepaliFunctions.BS2AD(bsDate);
                    if (adDate) {
                        startAd.value = NepaliFunctions.ConvertToDateFormat(adDate, 'YYYY-MM-DD');
                    }
                }
            }
        });

        endBs.nepaliDatePicker({
            dateFormat: 'YYYY-MM-DD',
            language: 'english',
            mode: 'light',
            container: 'body',
            onSelect: function(dateObj) {
                if (dateObj && dateObj.value) {
                    const bsDate = NepaliFunctions.ConvertToDateObject(dateObj.value, 'YYYY-MM-DD');
                    const adDate = NepaliFunctions.BS2AD(bsDate);
                    if (adDate) {
                        endAd.value = NepaliFunctions.ConvertToDateFormat(adDate, 'YYYY-MM-DD');
                    }
                }
            }
        });

        // Re-add readonly after initialization and prevent typing
        startBs.setAttribute('readonly', 'readonly');
        endBs.setAttribute('readonly', 'readonly');
        
        startBs.addEventListener('keydown', function(e) {
            e.preventDefault();
        });
        
        endBs.addEventListener('keydown', function(e) {
            e.preventDefault();
        });
        
        // Add click handlers to position calendar properly
        startBs.addEventListener('click', function() {
            setTimeout(function() {
                const calendar = document.querySelector('.ndp-container');
                if (calendar) {
                    const rect = startBs.getBoundingClientRect();
                    const spaceBelow = window.innerHeight - rect.bottom;
                    
                    calendar.style.position = 'fixed';
                    
                    if (spaceBelow >= 300) {
                        calendar.style.top = (rect.bottom + 2) + 'px';
                    } else {
                        calendar.style.top = (rect.top - calendar.offsetHeight - 2) + 'px';
                    }
                    calendar.style.left = rect.left + 'px';
                    
                    // Close calendar on scroll
                    const closeOnScroll = function() {
                        if (calendar && calendar.parentNode) {
                            calendar.remove();
                        }
                        window.removeEventListener('scroll', closeOnScroll, true);
                    };
                    window.addEventListener('scroll', closeOnScroll, true);
                }
            }, 10);
        });
        
        endBs.addEventListener('click', function() {
            setTimeout(function() {
                const calendar = document.querySelector('.ndp-container');
                if (calendar) {
                    const rect = endBs.getBoundingClientRect();
                    const spaceBelow = window.innerHeight - rect.bottom;
                    
                    calendar.style.position = 'fixed';
                    
                    if (spaceBelow >= 300) {
                        calendar.style.top = (rect.bottom + 2) + 'px';
                    } else {
                        calendar.style.top = (rect.top - calendar.offsetHeight - 2) + 'px';
                    }
                    calendar.style.left = rect.left + 'px';
                    
                    // Close calendar on scroll
                    const closeOnScroll = function() {
                        if (calendar && calendar.parentNode) {
                            calendar.remove();
                        }
                        window.removeEventListener('scroll', closeOnScroll, true);
                    };
                    window.addEventListener('scroll', closeOnScroll, true);
                }
            }, 10);
        });

        // Sync AD to BS when AD field changes
        startAd.addEventListener('change', function() {
            const adVal = startAd.value;
            if (adVal) {
                try {
                    const adDate = NepaliFunctions.ConvertToDateObject(adVal, 'YYYY-MM-DD');
                    const bsDate = NepaliFunctions.AD2BS(adDate);
                    if (bsDate) {
                        startBs.value = NepaliFunctions.ConvertToDateFormat(bsDate, 'YYYY-MM-DD');
                    }
                } catch (e) {
                    console.error('Error converting AD to BS:', e);
                }
            } else {
                startBs.value = '';
            }
        });

        endAd.addEventListener('change', function() {
            const adVal = endAd.value;
            if (adVal) {
                try {
                    const adDate = NepaliFunctions.ConvertToDateObject(adVal, 'YYYY-MM-DD');
                    const bsDate = NepaliFunctions.AD2BS(adDate);
                    if (bsDate) {
                        endBs.value = NepaliFunctions.ConvertToDateFormat(bsDate, 'YYYY-MM-DD');
                    }
                } catch (e) {
                    console.error('Error converting AD to BS:', e);
                }
            } else {
                endBs.value = '';
            }
        });
    }

    // Initialize timeline date pickers (dynamically added rows)
    function initTimelineDatePickers() {
        if (typeof NepaliFunctions === 'undefined' || typeof HTMLElement.prototype.nepaliDatePicker === 'undefined') {
            return;
        }

        const timelineBsFields = document.querySelectorAll('.timeline-date-bs');
        
        timelineBsFields.forEach(function(bsField, index) {
            // Skip if already initialized
            if (bsField.dataset.ndpInitialized) {
                return;
            }
            
            bsField.dataset.ndpInitialized = 'true';
            
            // Find the corresponding AD field in the same row
            const row = bsField.closest('.timeline-row');
            if (!row) {
                return;
            }
            
            const adField = row.querySelector('.timeline-date-ad');
            if (!adField) {
                return;
            }
            
            // Temporarily remove readonly to allow datepicker to work
            bsField.removeAttribute('readonly');
            
            // Initialize datepicker
            try {
                bsField.nepaliDatePicker({
                    dateFormat: 'YYYY-MM-DD',
                    language: 'english',
                    mode: 'light',
                    container: 'body',
                    onSelect: function(dateObj) {
                        if (dateObj && dateObj.value) {
                            const bsDate = NepaliFunctions.ConvertToDateObject(dateObj.value, 'YYYY-MM-DD');
                            const adDate = NepaliFunctions.BS2AD(bsDate);
                            if (adDate) {
                                adField.value = NepaliFunctions.ConvertToDateFormat(adDate, 'YYYY-MM-DD');
                                // Trigger change event for widget to update
                                adField.dispatchEvent(new Event('change', { bubbles: true }));
                            }
                        }
                    }
                });
                
                // Add click handler to position calendar properly
                bsField.addEventListener('click', function() {
                    setTimeout(function() {
                        const calendar = document.querySelector('.ndp-container');
                        if (calendar) {
                            const rect = bsField.getBoundingClientRect();
                            const spaceBelow = window.innerHeight - rect.bottom;
                            
                            // Use fixed positioning to attach to the input box
                            calendar.style.position = 'fixed';
                            
                            // Position calendar below or above the field based on available space
                            if (spaceBelow >= 300) {
                                calendar.style.top = (rect.bottom + 2) + 'px';
                            } else {
                                calendar.style.top = (rect.top - calendar.offsetHeight - 2) + 'px';
                            }
                            calendar.style.left = rect.left + 'px';
                            
                            // Close calendar on scroll
                            const closeOnScroll = function() {
                                if (calendar && calendar.parentNode) {
                                    calendar.remove();
                                }
                                window.removeEventListener('scroll', closeOnScroll, true);
                            };
                            window.addEventListener('scroll', closeOnScroll, true);
                        }
                    }, 10);
                });
                
                // Make field readonly after initialization to prevent manual typing
                bsField.setAttribute('readonly', 'readonly');
                
                // Prevent typing but allow clicking
                bsField.addEventListener('keydown', function(e) {
                    e.preventDefault();
                });
            } catch (e) {
                console.error('Error initializing timeline datepicker:', e);
            }
            
            // Sync AD to BS when AD changes
            adField.addEventListener('change', function() {
                const adVal = adField.value;
                if (adVal) {
                    try {
                        const adDate = NepaliFunctions.ConvertToDateObject(adVal, 'YYYY-MM-DD');
                        const bsDate = NepaliFunctions.AD2BS(adDate);
                        if (bsDate) {
                            bsField.value = NepaliFunctions.ConvertToDateFormat(bsDate, 'YYYY-MM-DD');
                        }
                    } catch (e) {
                        console.error('Error converting AD to BS:', e);
                    }
                } else {
                    bsField.value = '';
                }
            });
        });
    }

    // Watch for new timeline rows being added
    const timelineObserver = new MutationObserver(function(mutations) {
        let shouldInit = false;
        mutations.forEach(function(mutation) {
            mutation.addedNodes.forEach(function(node) {
                if (node.classList && node.classList.contains('timeline-row')) {
                    shouldInit = true;
                }
                // Also check if timeline fields were added inside a node
                if (node.querySelectorAll) {
                    const timelineFields = node.querySelectorAll('.timeline-date-bs');
                    if (timelineFields.length > 0) {
                        shouldInit = true;
                    }
                }
            });
        });
        if (shouldInit) {
            setTimeout(initTimelineDatePickers, 200);
        }
    });
    
    // Expose function globally for manual initialization
    window.initTimelineDatePickers = initTimelineDatePickers;
    
    // Start observing after page load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            timelineObserver.observe(document.body, { childList: true, subtree: true });
            setTimeout(initTimelineDatePickers, 1500);
        });
    } else {
        timelineObserver.observe(document.body, { childList: true, subtree: true });
        setTimeout(initTimelineDatePickers, 1500);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
