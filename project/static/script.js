// Form handling for signup and login
document.querySelector('#signup-form form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const button = this.querySelector('.btn-submit');
    button.innerHTML = '<span>Please wait...</span><i class="fas fa-spinner fa-spin"></i>';
    button.disabled = true;

    const formData = {
        username: this.querySelector('input[name="username"]').value,
        email: this.querySelector('input[name="email"]').value,
        password: this.querySelector('input[name="password"]').value,
        strand: this.querySelector('select[name="strand"]').value
    };

    try {
        const response = await fetch('/signup', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (response.ok) {
            // Show OTP verification form
            toggleForm('otp');
            document.querySelector('.user-email').textContent = formData.email;
            startOtpTimer();
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('Something went wrong!', 'error');
    } finally {
        button.innerHTML = '<span>Create Account</span><i class="fas fa-arrow-right"></i>';
        button.disabled = false;
    }
});

document.querySelector('#login-form form').addEventListener('submit', async function(e) {
    e.preventDefault();
    const button = this.querySelector('.btn-submit');
    button.innerHTML = '<span>Please wait...</span><i class="fas fa-spinner fa-spin"></i>';
    button.disabled = true;

    const formData = {
        email: this.querySelector('input[name="email"]').value,
        password: this.querySelector('input[name="password"]').value
    };

    try {
        const response = await fetch('/login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();

        if (response.ok) {
            window.location.href = '/dashboard';
        } else {
            showNotification(data.error, 'error');
        }
    } catch (error) {
        showNotification('Something went wrong!', 'error');
    } finally {
        button.innerHTML = '<span>Login</span><i class="fas fa-arrow-right"></i>';
        button.disabled = false;
    }
});

// OTP form handling
if (document.querySelector('#otp-form')) {
    document.querySelector('#otp-form form').addEventListener('submit', async function(e) {
        e.preventDefault();
        const button = this.querySelector('.btn-submit');
        button.innerHTML = '<span>Verifying...</span><i class="fas fa-spinner fa-spin"></i>';
        button.disabled = true;

        const inputs = Array.from(this.querySelectorAll('.otp-inputs input'));
        const otp = inputs.map(input => input.value).join('');

        try {
            const response = await fetch('/verify-otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    email: document.querySelector('.user-email').textContent,
                    otp: otp
                })
            });

            const data = await response.json();

            if (response.ok) {
                showNotification('Account verified successfully!', 'success');
                setTimeout(() => {
                    window.location.href = '/dashboard';
                }, 1500);
            } else {
                showNotification(data.error, 'error');
                button.innerHTML = '<span>Verify Code</span><i class="fas fa-check-circle"></i>';
                button.disabled = false;
            }
        } catch (error) {
            showNotification('Something went wrong!', 'error');
            button.innerHTML = '<span>Verify Code</span><i class="fas fa-check-circle"></i>';
            button.disabled = false;
        }
    });
}

// Password visibility toggle
const toggleButtons = document.querySelectorAll('.toggle-password');
toggleButtons.forEach(button => {
    button.addEventListener('click', function() {
        const input = this.previousElementSibling;
        const type = input.type === 'password' ? 'text' : 'password';
        input.type = type;
        this.classList.toggle('fa-eye');
        this.classList.toggle('fa-eye-slash');
    });
});

// Form switching
function toggleForm(formType) {
    const forms = document.querySelectorAll('.auth-form');
    forms.forEach(form => {
        if (form.id === formType + '-form') {
            form.classList.remove('hidden');
        } else {
            form.classList.add('hidden');
        }
    });
}

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <i class="fas ${type === 'success' ? 'fa-check-circle' : 'fa-exclamation-circle'}"></i>
        <span>${message}</span>
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => notification.classList.add('show'), 100);
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// OTP timer
function startOtpTimer() {
    const timerElement = document.querySelector('#timer');
    if (!timerElement) return;

    let timeLeft = 600; // 10 minutes in seconds
    const timerInterval = setInterval(() => {
        const minutes = Math.floor(timeLeft / 60);
        const seconds = timeLeft % 60;
        
        timerElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
        
        if (timeLeft === 0) {
            clearInterval(timerInterval);
            document.querySelector('#resendBtn').disabled = false;
        } else {
            timeLeft--;
        }
    }, 1000);
}