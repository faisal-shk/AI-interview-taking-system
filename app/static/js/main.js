// Main JavaScript for Interview Platform

document.addEventListener('DOMContentLoaded', function() {
    // Auto close alerts after 5 seconds
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(alert => {
        setTimeout(() => {
            const closeButton = alert.querySelector('.btn-close');
            if (closeButton) {
                closeButton.click();
            }
        }, 5000);
    });

    // Tooltip initialization (if Bootstrap 5 tooltips are used)
    if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => {
            new bootstrap.Tooltip(tooltip);
        });
    }

    // Add active class to current nav item
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.navbar-nav .nav-link');
    
    navLinks.forEach(link => {
        const href = link.getAttribute('href');
        if (href && currentPath.startsWith(href) && href !== '/') {
            link.classList.add('active');
        }
    });

    // Form validation enhancement
    const forms = document.querySelectorAll('form.needs-validation');
    forms.forEach(form => {
        form.addEventListener('submit', event => {
            if (!form.checkValidity()) {
                event.preventDefault();
                event.stopPropagation();
            }
            
            form.classList.add('was-validated');
        });
    });

    // Handle file input display (showing selected filename)
    const fileInputs = document.querySelectorAll('input[type="file"]');
    fileInputs.forEach(input => {
        input.addEventListener('change', event => {
            const fileName = event.target.files[0]?.name || 'No file selected';
            const fileNameDisplay = document.querySelector(`[data-file-display="${input.id}"]`);
            
            if (fileNameDisplay) {
                fileNameDisplay.textContent = fileName;
            }
        });
    });

    // Confirmation dialogs
    const confirmButtons = document.querySelectorAll('[data-confirm]');
    confirmButtons.forEach(button => {
        button.addEventListener('click', event => {
            const message = button.getAttribute('data-confirm') || 'Are you sure?';
            if (!confirm(message)) {
                event.preventDefault();
            }
        });
    });
});

// Speech recognition utilities
const SpeechRecognitionUtil = {
    isSupported: function() {
        return 'webkitSpeechRecognition' in window || 'SpeechRecognition' in window;
    },
    
    create: function(options = {}) {
        if (!this.isSupported()) {
            console.error('Speech recognition is not supported in this browser');
            return null;
        }
        
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        
        // Default options
        recognition.continuous = options.continuous !== undefined ? options.continuous : true;
        recognition.interimResults = options.interimResults !== undefined ? options.interimResults : true;
        recognition.lang = options.lang || 'en-US';
        
        return recognition;
    }
};

// Copy to clipboard utility
function copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text)
            .then(() => {
                showToast('Copied to clipboard!');
            })
            .catch(err => {
                console.error('Could not copy text: ', err);
            });
    } else {
        // Fallback for older browsers
        const textarea = document.createElement('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        
        try {
            const successful = document.execCommand('copy');
            if (successful) {
                showToast('Copied to clipboard!');
            } else {
                console.error('Copy command was unsuccessful');
            }
        } catch (err) {
            console.error('Could not copy text: ', err);
        }
        
        document.body.removeChild(textarea);
    }
}

// Toast notification utility
function showToast(message, type = 'success', duration = 3000) {
    const toastContainer = document.getElementById('toast-container');
    
    if (!toastContainer) {
        // Create toast container if it doesn't exist
        const container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'position-fixed bottom-0 end-0 p-3';
        container.style.zIndex = '1050';
        document.body.appendChild(container);
    }
    
    const toastId = 'toast-' + Math.random().toString(36).substr(2, 9);
    const toast = document.createElement('div');
    toast.className = `toast bg-${type} text-white`;
    toast.id = toastId;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="toast-header bg-${type} text-white">
            <strong class="me-auto">Notification</strong>
            <button type="button" class="btn-close btn-close-white" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
        <div class="toast-body">
            ${message}
        </div>
    `;
    
    document.getElementById('toast-container').appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast, {
        autohide: true,
        delay: duration
    });
    
    bsToast.show();
    
    // Remove toast from DOM after it's hidden
    toast.addEventListener('hidden.bs.toast', function () {
        document.getElementById('toast-container').removeChild(toast);
    });
} 