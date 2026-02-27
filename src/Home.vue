<script>
export default {
  name: 'HomePage'
}
</script>

<template>
  <div class="home-container">
    <div class="background-animation"></div>
    <div class="content-wrapper">
      <div class="name-container">
        <h1 class="main-title">
          <span class="char" style="--delay: 0s">张</span>
          <span class="char" style="--delay: 0.2s">红</span>
          <span class="char" style="--delay: 0.4s">星</span>
        </h1>
        <div class="glow-effect"></div>
      </div>
      <div class="subtitle">
        <p class="typing-text">欢迎来到我的个人主页</p>
      </div>
      <div class="floating-elements">
        <div class="circle circle-1"></div>
        <div class="circle circle-2"></div>
        <div class="circle circle-3"></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

.home-container {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.background-animation {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: 
    radial-gradient(circle at 20% 50%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 80% 20%, rgba(255, 255, 255, 0.1) 0%, transparent 50%),
    radial-gradient(circle at 40% 80%, rgba(255, 255, 255, 0.1) 0%, transparent 50%);
  animation: pulse 4s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 0.5;
    transform: scale(1);
  }
  50% {
    opacity: 1;
    transform: scale(1.1);
  }
}

.content-wrapper {
  position: relative;
  z-index: 10;
  text-align: center;
}

.name-container {
  position: relative;
  display: inline-block;
}

.main-title {
  font-size: 80px;
  font-weight: 900;
  color: #ffffff;
  text-shadow: 
    0 0 10px rgba(255, 107, 107, 0.8),
    0 0 20px rgba(254, 202, 87, 0.8),
    0 0 30px rgba(72, 219, 251, 0.8),
    0 0 40px rgba(255, 159, 243, 0.8);
  letter-spacing: 30px;
  margin: 0;
  padding: 20px;
  animation: colorChange 3s ease infinite;
}

@keyframes colorChange {
  0%, 100% {
    color: #ff6b6b;
    text-shadow: 0 0 20px #ff6b6b, 0 0 40px #ff6b6b;
  }
  25% {
    color: #feca57;
    text-shadow: 0 0 20px #feca57, 0 0 40px #feca57;
  }
  50% {
    color: #48dbfb;
    text-shadow: 0 0 20px #48dbfb, 0 0 40px #48dbfb;
  }
  75% {
    color: #ff9ff3;
    text-shadow: 0 0 20px #ff9ff3, 0 0 40px #ff9ff3;
  }
}

.char {
  display: inline-block;
  animation: float 2s ease-in-out infinite;
  animation-delay: var(--delay);
}

@keyframes float {
  0%, 100% {
    transform: translateY(0) rotate(0deg);
  }
  50% {
    transform: translateY(-20px) rotate(5deg);
  }
}

.glow-effect {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.3) 0%, transparent 70%);
  border-radius: 50%;
  animation: glow 2s ease-in-out infinite;
  z-index: -1;
}

@keyframes glow {
  0%, 100% {
    opacity: 0.5;
    transform: translate(-50%, -50%) scale(1);
  }
  50% {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1.2);
  }
}

.subtitle {
  margin-top: 40px;
}

.typing-text {
  font-size: 28px;
  color: rgba(255, 255, 255, 0.9);
  letter-spacing: 5px;
  animation: typing 3s steps(10) infinite;
  overflow: hidden;
  white-space: nowrap;
  border-right: 3px solid rgba(255, 255, 255, 0.8);
  display: inline-block;
  padding-right: 5px;
}

@keyframes typing {
  0%, 100% {
    width: 0;
  }
  50%, 90% {
    width: 100%;
  }
}

.floating-elements {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  animation: floatCircle 6s ease-in-out infinite;
}

.circle-1 {
  width: 100px;
  height: 100px;
  top: 10%;
  left: 10%;
  animation-delay: 0s;
}

.circle-2 {
  width: 150px;
  height: 150px;
  top: 60%;
  right: 15%;
  animation-delay: 2s;
}

.circle-3 {
  width: 80px;
  height: 80px;
  bottom: 15%;
  left: 20%;
  animation-delay: 4s;
}

@keyframes floatCircle {
  0%, 100% {
    transform: translateY(0) translateX(0);
    opacity: 0.3;
  }
  25% {
    transform: translateY(-30px) translateX(20px);
    opacity: 0.6;
  }
  50% {
    transform: translateY(-10px) translateX(-20px);
    opacity: 0.4;
  }
  75% {
    transform: translateY(-40px) translateX(10px);
    opacity: 0.7;
  }
}
</style>
