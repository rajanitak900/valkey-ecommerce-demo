const fs = require('fs');
const path = require('path');
const https = require('https');

const imagesDir = path.join(__dirname, 'public', 'assets', 'images');

// 1.5x larger dimensions so the logo naturally takes up more space and is much easier to read!
// Original: 235x51 -> New: 352x76
// Original: 293x44 -> New: 440x66
const logos = [
  { file: 'logo/logo.png', url: 'https://placehold.co/352x76/27AE60/FFFFFF/png?text=SnapBasket&font=Montserrat' },
  { file: 'logo/logo-two.png', url: 'https://placehold.co/440x66/27AE60/FFFFFF/png?text=SnapBasket&font=Montserrat' },
  { file: 'logo/logo-two-black.png', url: 'https://placehold.co/440x66/27AE60/FFFFFF/png?text=SnapBasket&font=Montserrat' }
];

function download(url, dest) {
  return new Promise((resolve, reject) => {
    const request = https.get(url, (response) => {
      if (response.statusCode === 301 || response.statusCode === 302) {
        download(response.headers.location, dest).then(resolve).catch(reject);
        return;
      }
      if (response.statusCode !== 200) {
        reject(new Error(`Failed to get '${url}' (Status Code: ${response.statusCode})`));
        return;
      }
      const file = fs.createWriteStream(dest);
      response.pipe(file);
      file.on('finish', () => {
        file.close();
        resolve();
      });
    });
    request.on('error', (err) => {
      fs.unlink(dest, () => reject(err));
    });
  });
}

async function run() {
  console.log('Downloading larger logos...');
  
  for (const item of logos) {
    const fullPath = path.join(imagesDir, item.file);
    console.log(`Overwriting logo: ${item.file}`);
    await download(item.url, fullPath);
  }
  
  console.log('Done!');
}

run();
