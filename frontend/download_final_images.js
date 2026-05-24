const fs = require('fs');
const path = require('path');
const https = require('https');

const imagesDir = path.join(__dirname, 'public', 'assets', 'images');

const logos = [
  'logo/logo-two-black.png',
  'logo/logo-two.png',
  'logo/logo.png',
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

function walk(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  list.forEach(file => {
    const fullPath = path.join(dir, file);
    const stat = fs.statSync(fullPath);
    if (stat && stat.isDirectory()) {
      results = results.concat(walk(fullPath));
    } else if (file.endsWith('.png') || file.endsWith('.jpg') || file.endsWith('.jpeg')) {
      if (stat.size < 15000) {
        results.push(fullPath);
      }
    }
  });
  return results;
}

async function run() {
  console.log('Finding placeholder images...');
  
  for (const logo of logos) {
    const fullPath = path.join(imagesDir, logo);
    if (fs.existsSync(fullPath)) {
      console.log(`Overwriting logo: ${logo}`);
      await download('https://placehold.co/235x51/27AE60/FFFFFF/png?text=SnapBasket&font=Montserrat', fullPath);
    }
  }

  const smallImages = walk(imagesDir);
  for (const imgPath of smallImages) {
    if (imgPath.includes('logo\\') || imgPath.includes('logo/')) continue;
    if (imgPath.includes('icon\\') || imgPath.includes('icon/')) continue;
    if (imgPath.includes('shape\\') || imgPath.includes('shape/')) continue;

    console.log(`Downloading replacement for: ${imgPath.replace(imagesDir, '')}`);
    const w = 600 + Math.floor(Math.random() * 100);
    const h = 600 + Math.floor(Math.random() * 100);
    
    // Using picsum because loremflickr can sometimes be unreliable/rate limited
    // The user just wants placeholders replaced, let's use Picsum!
    try {
      await download(`https://picsum.photos/${w}/${h}`, imgPath);
    } catch (e) {
      console.error(`Failed to download for ${imgPath}:`, e.message);
    }
    await new Promise(r => setTimeout(r, 100));
  }
  
  console.log('Done downloading all replacement images!');
}

run();
