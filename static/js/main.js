// Smart Lender Front-End JavaScript Application Layer

document.addEventListener('DOMContentLoaded', function () {
    // 1. Theme Management (Dark / Light Mode)
    const themeSwitcher = document.getElementById('theme-switcher');
    const themeIcon = themeSwitcher ? themeSwitcher.querySelector('i') : null;
    
    // Check local storage or system preference
    const savedTheme = localStorage.getItem('theme') || 'dark';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeIcon(savedTheme);
    
    if (themeSwitcher) {
        themeSwitcher.addEventListener('click', function () {
            const currentTheme = document.documentElement.getAttribute('data-theme');
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            document.documentElement.setAttribute('data-theme', newTheme);
            localStorage.setItem('theme', newTheme);
            updateThemeIcon(newTheme);
        });
    }
    
    function updateThemeIcon(theme) {
        if (!themeIcon) return;
        if (theme === 'dark') {
            themeIcon.className = 'fas fa-sun text-warning';
        } else {
            themeIcon.className = 'fas fa-moon text-primary';
        }
    }
    
    // 2. Accessibility: Font Resizing
    const btnIncreaseFont = document.getElementById('btn-increase-font');
    const btnDecreaseFont = document.getElementById('btn-decrease-font');
    const btnResetFont = document.getElementById('btn-reset-font');
    let currentFontSize = 100; // in percentage
    
    if (btnIncreaseFont && btnDecreaseFont && btnResetFont) {
        btnIncreaseFont.addEventListener('click', function() {
            if (currentFontSize < 130) {
                currentFontSize += 10;
                document.body.style.fontSize = currentFontSize + '%';
            }
        });
        
        btnDecreaseFont.addEventListener('click', function() {
            if (currentFontSize > 80) {
                currentFontSize -= 10;
                document.body.style.fontSize = currentFontSize + '%';
            }
        });
        
        btnResetFont.addEventListener('click', function() {
            currentFontSize = 100;
            document.body.style.fontSize = '100%';
        });
    }

    // 3. EMI Calculator Interactivity
    const emiForm = document.getElementById('emi-calculator-form');
    if (emiForm) {
        emiForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const principal = parseFloat(document.getElementById('emi-principal').value);
            const rate = parseFloat(document.getElementById('emi-rate').value);
            const term = parseFloat(document.getElementById('emi-term').value);
            
            fetch('/emi-calculator', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ principal, rate, term })
            })
            .then(res => res.json())
            .then(data => {
                // Populate UI
                document.getElementById('emi-result-monthly').innerText = '$' + data.emi.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                document.getElementById('emi-result-interest').innerText = '$' + data.total_interest.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                document.getElementById('emi-result-total').innerText = '$' + data.total_payment.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2});
                
                // Show result container
                const container = document.getElementById('emi-result-container');
                if (container) container.classList.remove('d-none');
            })
            .catch(err => console.error("EMI Calculation Error:", err));
        });
    }

    // 4. Loan Comparison Interactivity
    const compForm = document.getElementById('loan-comparison-form');
    if (compForm) {
        compForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const principal = parseFloat(document.getElementById('comp-principal').value);
            const term = parseFloat(document.getElementById('comp-term').value);
            const ratesInput = document.getElementById('comp-rates').value;
            // Parse comma-separated rates
            const rates = ratesInput.split(',').map(r => parseFloat(r.trim())).filter(r => !isNaN(r));
            
            fetch('/compare-loans', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ principal, term, rates })
            })
            .then(res => res.json())
            .then(data => {
                const resultsTbody = document.getElementById('comp-results-tbody');
                if (resultsTbody) {
                    resultsTbody.innerHTML = '';
                    data.forEach(item => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td><b>${item.rate}%</b></td>
                            <td>$${item.emi.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            <td>$${item.total_interest.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                            <td>$${item.total_payment.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                        `;
                        resultsTbody.appendChild(tr);
                    });
                }
                
                const container = document.getElementById('comp-result-container');
                if (container) container.classList.remove('d-none');
            })
            .catch(err => console.error("Loan Comparison Error:", err));
        });
    }
});

// 5. Toast Notification Helper
function showToast(message, type = 'success') {
    const toastContainer = document.getElementById('toast-container');
    if (!toastContainer) return;
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0 show m-2`;
    toast.role = 'alert';
    toast.ariaLive = 'assertive';
    toast.ariaAtomic = 'true';
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto-remove after 4 seconds
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 500);
    }, 4000);
}
