const fs = require('fs');
const path = require('path');
const https = require('https');

const IMAGES = {
  // Popular Images
  'thumbs/popular-img1.png': 'https://images.unsplash.com/photo-1597362925123-77861d3fbac7?auto=format&fit=crop&q=80&w=200',
  'thumbs/popular-img2.png': 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&q=80&w=200',
  'thumbs/popular-img3.png': 'https://images.unsplash.com/photo-1610832958506-aa56368176cf?auto=format&fit=crop&q=80&w=200',
  'thumbs/popular-img4.png': 'https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&q=80&w=200',
  'thumbs/popular-img5.png': 'https://images.unsplash.com/photo-1603048588665-791ca8aea617?auto=format&fit=crop&q=80&w=200',
  'thumbs/popular-img6.png': 'https://images.unsplash.com/photo-1534482421-64566f976cfa?auto=format&fit=crop&q=80&w=200',
  'thumbs/popular-img7.png': 'https://images.unsplash.com/photo-1550583724-b2692b85b150?auto=format&fit=crop&q=80&w=200',
  'thumbs/popular-img8.png': 'https://images.unsplash.com/photo-1587314168485-3236d6710814?auto=format&fit=crop&q=80&w=200',

  // Blog Images
  'thumbs/blog-img1.png': 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&q=80&w=600',
  'thumbs/blog-img2.png': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&q=80&w=600',
  'thumbs/blog-img3.png': 'https://images.unsplash.com/photo-1472851294608-062f824d29cc?auto=format&fit=crop&q=80&w=600',
  'thumbs/blog-details-img1.png': 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&q=80&w=800',
  'thumbs/blog-details-img2.png': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&q=80&w=800',

  // Instagram
  'thumbs/instagram-img1.png': 'https://images.unsplash.com/photo-1612817288484-6f916006741a?auto=format&fit=crop&q=80&w=300',
  'thumbs/instagram-img2.png': 'https://images.unsplash.com/photo-1534723328310-e82dad3ee43f?auto=format&fit=crop&q=80&w=300',
  'thumbs/instagram-img3.png': 'https://images.unsplash.com/photo-1473186578172-c141e6798cf4?auto=format&fit=crop&q=80&w=300',
  'thumbs/instagram-img4.png': 'https://images.unsplash.com/photo-1506617564039-2f3b650b7010?auto=format&fit=crop&q=80&w=300',

  // Best Selling / Trending / Flash Sale
  'thumbs/best-sell1.png': 'https://images.unsplash.com/photo-1581798459219-318e76aecc7b?auto=format&fit=crop&q=80&w=150',
  'thumbs/best-sell2.png': 'https://images.unsplash.com/photo-1599490659213-e2b9527bc087?auto=format&fit=crop&q=80&w=150',
  'thumbs/best-sell3.png': 'https://images.unsplash.com/photo-1548598146-f8441d36097c?auto=format&fit=crop&q=80&w=150',
  'thumbs/best-sell4.png': 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?auto=format&fit=crop&q=80&w=150',
  
  'thumbs/best-selling-img1.png': 'https://images.unsplash.com/photo-1597362925123-77861d3fbac7?auto=format&fit=crop&q=80&w=150',
  'thumbs/best-selling-img2.png': 'https://images.unsplash.com/photo-1534482421-64566f976cfa?auto=format&fit=crop&q=80&w=150',
  'thumbs/best-selling-img3.png': 'https://images.unsplash.com/photo-1587314168485-3236d6710814?auto=format&fit=crop&q=80&w=150',
  'thumbs/best-selling-img4.png': 'https://images.unsplash.com/photo-1621506289937-a8e4df240d0b?auto=format&fit=crop&q=80&w=150',
  'thumbs/best-selling-img5.png': 'https://images.unsplash.com/photo-1583337130417-3346a1be7dee?auto=format&fit=crop&q=80&w=150',
  'thumbs/best-selling-img6.png': 'https://images.unsplash.com/photo-1619546813926-a78fa6372cd2?auto=format&fit=crop&q=80&w=150',
  
  'thumbs/flash-sale-img1.png': 'https://images.unsplash.com/photo-1560806887-1e4cd0b6cbd6?auto=format&fit=crop&q=80&w=300',
  'thumbs/flash-sale-img2.png': 'https://images.unsplash.com/photo-1571771894821-ce9b6c11b08e?auto=format&fit=crop&q=80&w=300',
  'thumbs/day-sale-img1.png': 'https://images.unsplash.com/photo-1610832958506-aa56368176cf?auto=format&fit=crop&q=80&w=300',
  'thumbs/day-sale-img2.png': 'https://images.unsplash.com/photo-1563636619-e9143da7973b?auto=format&fit=crop&q=80&w=300',

  // Top Brands / Store images
  'thumbs/top-brand-img1.png': 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&q=80&w=150',
  'thumbs/top-brand-img2.png': 'https://images.unsplash.com/photo-1473186578172-c141e6798cf4?auto=format&fit=crop&q=80&w=150',
  'thumbs/top-brand-img3.png': 'https://images.unsplash.com/photo-1534723328310-e82dad3ee43f?auto=format&fit=crop&q=80&w=150',
  'thumbs/top-brand-img4.png': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&q=80&w=150',
  'thumbs/top-brand-img5.png': 'https://images.unsplash.com/photo-1472851294608-062f824d29cc?auto=format&fit=crop&q=80&w=150',
  'thumbs/top-brand-img6.png': 'https://images.unsplash.com/photo-1506617564039-2f3b650b7010?auto=format&fit=crop&q=80&w=150',
  'thumbs/top-brand-img7.png': 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&q=80&w=150',
  'thumbs/top-brand-img8.png': 'https://images.unsplash.com/photo-1473186578172-c141e6798cf4?auto=format&fit=crop&q=80&w=150',

  'thumbs/store-img1.png': 'https://images.unsplash.com/photo-1534723328310-e82dad3ee43f?auto=format&fit=crop&q=80&w=150',
  'thumbs/store-img2.png': 'https://images.unsplash.com/photo-1441986300917-64674bd600d8?auto=format&fit=crop&q=80&w=150',

  // Avatars / Comments / Testimonials
  'thumbs/comment-img1.png': 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=100',
  'thumbs/comment-img2.png': 'https://images.unsplash.com/photo-1599566150163-29194dcaad36?auto=format&fit=crop&q=80&w=100',
  'thumbs/comment-img3.png': 'https://images.unsplash.com/photo-1527980965255-d3b416303d12?auto=format&fit=crop&q=80&w=100',
  'thumbs/comment-img4.png': 'https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&q=80&w=100',
  'thumbs/comment-img5.png': 'https://images.unsplash.com/photo-1438761681033-6461ffad8d80?auto=format&fit=crop&q=80&w=100',
  'thumbs/testimonials-img1.png': 'https://images.unsplash.com/photo-1535713875002-d1d0cf377fde?auto=format&fit=crop&q=80&w=150',
  'thumbs/testimonials-img2.png': 'https://images.unsplash.com/photo-1599566150163-29194dcaad36?auto=format&fit=crop&q=80&w=150',
  'thumbs/testimonials-img3.png': 'https://images.unsplash.com/photo-1527980965255-d3b416303d12?auto=format&fit=crop&q=80&w=150',
  'thumbs/testimonials-img4.png': 'https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&q=80&w=150',

  // Offers
  'thumbs/offer-img1.png': 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&q=80&w=400',
  'thumbs/offer-img2.png': 'https://images.unsplash.com/photo-1603048588665-791ca8aea617?auto=format&fit=crop&q=80&w=400',
  'thumbs/offer-logo.png': 'https://images.unsplash.com/photo-1516259762381-22954d7d3ad2?auto=format&fit=crop&q=80&w=100',

  // Misc
  'thumbs/delivery-man.png': 'https://images.unsplash.com/photo-1580674285054-bed31e145f59?auto=format&fit=crop&q=80&w=200',
  'thumbs/newsletter-img.png': 'https://images.unsplash.com/photo-1542838132-92c53300491e?auto=format&fit=crop&q=80&w=400'
};

const baseDir = path.join(__dirname, 'public', 'assets', 'images');

function download(url, dest) {
  return new Promise((resolve, reject) => {
    // Follow redirects
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
  console.log('Starting remaining images download...');
  for (const [relPath, url] of Object.entries(IMAGES)) {
    const fullPath = path.join(baseDir, relPath);
    const dir = path.dirname(fullPath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
    console.log(`Downloading to: ${relPath}`);
    try {
      await download(url, fullPath);
      console.log(`Success: ${relPath}`);
    } catch (err) {
      console.error(`Error downloading ${relPath}:`, err.message);
    }
  }
  console.log('Done downloading remaining images!');
}

run();
