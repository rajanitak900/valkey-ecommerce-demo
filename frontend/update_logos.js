const fs = require('fs');
const path = require('path');

const componentsDir = path.join(__dirname, 'src', 'components');
const files = fs.readdirSync(componentsDir).filter(f => f.endsWith('.jsx'));

files.forEach(file => {
  const filePath = path.join(componentsDir, file);
  let content = fs.readFileSync(filePath, 'utf-8');
  
  const imgRegex = /<img[^>]*src=['"]assets\/images\/logo\/logo[^>]*>/g;
  
  if (imgRegex.test(content)) {
    console.log(`Updating ${file}`);
    content = content.replace(imgRegex, '<h2 className="mb-0 text-main-600">SnapBasket</h2>');
    fs.writeFileSync(filePath, content, 'utf-8');
  }
});

console.log('Logo update complete.');
