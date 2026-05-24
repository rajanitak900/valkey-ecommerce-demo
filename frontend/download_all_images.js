const fs = require('fs');
const path = require('path');
const https = require('https');

const imagesDir = path.join(__dirname, 'public', 'assets', 'images');

const logos = [
  { file: 'logo/logo.png', url: 'https://placehold.co/235x51/27AE60/FFFFFF/png?text=SnapBasket&font=Montserrat' },
  { file: 'logo/logo-two.png', url: 'https://placehold.co/293x44/27AE60/FFFFFF/png?text=SnapBasket&font=Montserrat' },
  { file: 'logo/logo-two-black.png', url: 'https://placehold.co/293x44/27AE60/FFFFFF/png?text=SnapBasket&font=Montserrat' }
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
      results.push(fullPath);
    }
  });
  return results;
}

async function run() {
  console.log('Finding placeholder images...');
  
  for (const item of logos) {
    const fullPath = path.join(imagesDir, item.file);
    console.log(`Overwriting logo: ${item.file}`);
    await download(item.url, fullPath);
  }

  const allImages = walk(imagesDir);
  const toDownload = [];

  for (const imgPath of allImages) {
    if (imgPath.includes('logo\\') || imgPath.includes('logo/')) continue;
    if (imgPath.includes('icon\\') || imgPath.includes('icon/')) continue;
    if (imgPath.includes('shape\\') || imgPath.includes('shape/')) continue;

    // This time we overwrite EVERY image in thumbs/ and bg/ without size checks
    // to ensure NO placeholders are left.
    const w = 600 + Math.floor(Math.random() * 200);
    const h = 600 + Math.floor(Math.random() * 200);
    const url = `https://picsum.photos/${w}/${h}`;
    toDownload.push({ url, path: imgPath });
  }
  
  console.log(`Found ${toDownload.length} images to replace.`);

  // Process in batches of 20 for speed
  const BATCH_SIZE = 20;
  for (let i = 0; i < toDownload.length; i += BATCH_SIZE) {
    const batch = toDownload.slice(i, i + BATCH_SIZE);
    console.log(`Processing batch ${i / BATCH_SIZE + 1} / ${Math.ceil(toDownload.length / BATCH_SIZE)}`);
    await Promise.all(batch.map(item => 
      download(item.url, item.path).catch(e => console.error(`Failed ${item.path}`, e.message))
    ));
  }
  
  console.log('Done downloading all replacement images!');
}

run();
