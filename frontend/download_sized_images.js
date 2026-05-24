const fs = require('fs');
const path = require('path');
const https = require('https');

const imagesDir = path.join(__dirname, 'public', 'assets', 'images');

const logos = [
  'logo/logo.png',
  'logo/logo-two.png',
  'logo/logo-two-black.png'
];

function getPngDimensions(filePath) {
  try {
    const fd = fs.openSync(filePath, 'r');
    const buffer = Buffer.alloc(24);
    fs.readSync(fd, buffer, 0, 24, 0);
    fs.closeSync(fd);
    
    // Check if it's a PNG
    if (buffer[1] === 0x50 && buffer[2] === 0x4E && buffer[3] === 0x47) {
      return {
        width: buffer.readUInt32BE(16),
        height: buffer.readUInt32BE(20)
      };
    }
  } catch(e) {}
  return null;
}

function download(url, dest) {
  return new Promise((resolve, reject) => {
    const request = https.get(url, (response) => {
      if (response.statusCode === 301 || response.statusCode === 302) {
        const loc = response.headers.location;
        const newUrl = loc.startsWith('/') ? new URL(loc, url).href : loc;
        download(newUrl, dest).then(resolve).catch(reject);
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
    request.setTimeout(10000, () => {
        request.destroy();
        reject(new Error('Timeout'));
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
    } else if (file.endsWith('.png')) {
      results.push(fullPath);
    }
  });
  return results;
}

const keywords = ['grocery', 'food', 'supermarket', 'fresh', 'shopping', 'produce', 'vegetables', 'fruits'];

async function run() {
  console.log('Finding placeholder images...');
  
  // 1. Overwrite logos with SnapBasket placehold.co images explicitly
  for (const logo of logos) {
    const fullPath = path.join(imagesDir, logo);
    if (fs.existsSync(fullPath)) {
      const dim = getPngDimensions(fullPath);
      if (dim) {
        console.log(`Overwriting logo: ${logo} (${dim.width}x${dim.height})`);
        await download(`https://placehold.co/${dim.width}x${dim.height}/27AE60/FFFFFF/png?text=SnapBasket&font=Montserrat`, fullPath);
      }
    }
  }

  // 2. Walk and find all other placeholders that are < 15KB in size (meaning they are original grey template boxes)
  const allImages = walk(imagesDir);
  const toDownload = [];

  for (const imgPath of allImages) {
    if (imgPath.includes('logo\\') || imgPath.includes('logo/')) continue;
    if (imgPath.includes('icon\\') || imgPath.includes('icon/')) continue;
    if (imgPath.includes('shape\\') || imgPath.includes('shape/')) continue;

    const stat = fs.statSync(imgPath);
    // Only target placeholders (which are mostly < 15KB)
    if (stat.size < 15000) {
      const dim = getPngDimensions(imgPath);
      if (dim && dim.width > 10 && dim.height > 10) {
        // We will fetch a placeholder of EXACT dimension to ensure layout is flawless.
        // Using placehold.co or picsum.
        // The user asked for "pictures according to the description" -> so real pictures!
        // We will use loremflickr since it gives exact dimensions and themes!
        const kw = keywords[Math.floor(Math.random() * keywords.length)];
        // Add random cachebuster
        const cb = Math.floor(Math.random() * 100000);
        const url = `https://loremflickr.com/${dim.width}/${dim.height}/${kw}?lock=${cb}`;
        
        toDownload.push({ url, path: imgPath });
      }
    }
  }
  
  console.log(`Found ${toDownload.length} images to replace with EXACT dimensions.`);

  // Process in batches
  const BATCH_SIZE = 10;
  for (let i = 0; i < toDownload.length; i += BATCH_SIZE) {
    const batch = toDownload.slice(i, i + BATCH_SIZE);
    console.log(`Processing batch ${i / BATCH_SIZE + 1} / ${Math.ceil(toDownload.length / BATCH_SIZE)}`);
    await Promise.all(batch.map(item => 
      download(item.url, item.path).catch(e => console.error(`Failed ${item.path}`, e.message))
    ));
    await new Promise(r => setTimeout(r, 2000)); // Sleep 2 seconds to avoid rate limiting
  }
  
  console.log('Done downloading all strictly-sized replacement images!');
}

run();
