const puppeteer = require('puppeteer');
const path = require('path');

(async () => {
    try {
        const browser = await puppeteer.launch({
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        });
        const page = await browser.newPage();

        // Convert the absolute path to a file URL
        const htmlPath = path.resolve('/home/sephi-asi/FAIM/docs/Portfolio-Job/resume-cv.html');
        const fileUrl = `file://${htmlPath}`;

        await page.goto(fileUrl, { waitUntil: 'networkidle0' });

        // Generate the PDF
        const outputPath = path.resolve('/home/sephi-asi/FAIM/docs/Portfolio-Job/resume-cv.pdf');
        await page.pdf({
            path: outputPath,
            format: 'A4',
            printBackground: true, // IMPORTANT: true to show CSS background colors/images
            displayHeaderFooter: false,
            margin: {
                top: "10mm",
                bottom: "10mm",
                left: "10mm",
                right: "10mm"
            }
        });

        console.log(`PDF successfully generated at ${outputPath}`);
        await browser.close();
    } catch (error) {
        console.error('Error generating PDF:', error);
        process.exit(1);
    }
})();
