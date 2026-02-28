<script>
export default {
  name: 'Download'
}
</script>

<template>
  <div class="download-container">
    <div class="content">
      <div class="qrcode-container">
        <img 
          src="/images/phone.png" 
          alt="扫码下载APP" 
          class="qrcode-image"
        />
      </div>
      
      <div class="download-text">
        扫码下载
        <br>
        老年人智能手机打电话app
        <br>
        Android
      </div>
    </div>
  </div>
</template>

<style scoped>
.download-container {
  width: 100vw;
  height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.qrcode-container {
  margin-bottom: 30px;
}

.qrcode-image {
  width: 300px;
  height: 300px;
  border: 2px solid #ddd;
  border-radius: 10px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  transition: transform 0.3s ease;
}

.qrcode-image:hover {
  transform: scale(1.05);
}

.download-text {
  font-size: 18px;
  color: #fff;
  font-weight: 500;
  line-height: 1.6;
  text-shadow: 0 2px 4px rgba(0, 0, 0, 0.3);
}

@media (max-width: 480px) {
  .qrcode-image {
    width: 250px;
    height: 250px;
  }
  
  .download-text {
    font-size: 16px;
  }
}
</style>
