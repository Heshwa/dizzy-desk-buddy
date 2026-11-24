const {chromium} = require('../.work/npm/node_modules/playwright-core');
const path=require('node:path');
const assert=require('node:assert/strict');
(async()=>{
  const roots=path.resolve(__dirname,'..');
  const browser=await chromium.launch({headless:true,
    executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
    args:['--use-fake-device-for-media-stream','--use-fake-ui-for-media-stream',
       '--use-file-for-fake-audio-capture='+path.join(roots,'.work/browser-phrase.wav')]});
  const page=await browser.newPage({viewport:{width:1240,height:860},permissions:['microphone']});
  await page.addInitScript(() => { Math.random = () => .01; });
  const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  try {
    const origin=process.argv[2]||'http://127.0.0.1:8894';
    await page.request.post(origin+'/api/action',{data:{action:'phone_forget'}});
    await page.goto(origin);
    await page.getByRole('button',{name:'Soft smile',exact:true}).click();
    await page.getByText('Soft smile',{exact:true}).last().waitFor();
    await page.screenshot({path:path.join(roots,'reports/panel.png')});
    await page.getByRole('button',{name:'Movement',exact:true}).click();
    await page.getByRole('button',{name:'Shuffle',exact:true}).click();
    await page.getByText('Arm floor motion locally first.').waitFor();
    await page.getByRole('button',{name:'Music',exact:true}).click();
    await page.getByRole('button',{name:'Connect simulated phone'}).click();
    await page.getByRole('button',{name:'Play',exact:true}).click();
    await page.locator('#musicSummary').getByText(/^Playing /).waitFor();
    await page.getByRole('button',{name:'Start recording'}).click();
    await page.getByRole('button',{name:'Stop recording'}).waitFor();
    await page.waitForTimeout(2200);
    await page.getByRole('button',{name:'Stop recording'}).click();
    await page.getByRole('button',{name:'Start recording'}).waitFor();
    await page.locator('#history').getByText(/Look left/i).waitFor({timeout:30000});
    const reply=await page.locator('#history').innerText();
    assert.match(reply,/Dizzy: Turning my head to the left/);
    await page.getByRole('button',{name:'Games',exact:true}).click();
    await page.getByRole('button',{name:'Reaction timing',exact:true}).click();
    await page.getByRole('button',{name:'Tap!',exact:true}).click();
    await page.locator('#gamePrompt').getByText(/ms$/).waitFor();
    await page.getByRole('button',{name:'Memory sequence',exact:true}).click();
    await page.locator('#gamePrompt').getByText('Repeat the sequence.').waitFor();
    for(let step=0;step<4;step++) await page.locator('#gameBoard').getByRole('button',{name:'1',exact:true}).click();
    await page.locator('#gamePrompt').getByText('Sequence complete.').waitFor();
    await page.getByRole('button',{name:'Rhythm taps',exact:true}).click();
    await page.locator('#gameBoard button').evaluate(button=>{
      let beat=0;
      const cue=new MutationObserver(()=>{
        if(button.classList.contains('activeCue') && !button.disabled){
          button.click();
          if(++beat===4)cue.disconnect();
        }
      });
      cue.observe(button,{attributes:true,attributeFilter:['class']});
    });
    await page.locator('#gamePrompt').getByText('Four beats on time.').waitFor();
    await page.setViewportSize({width:390,height:820});
    assert.equal(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),true);
    assert.deepEqual(errors,[]);
    console.log(JSON.stringify({test:'PASS',fixture:'Chrome fake microphone',reply,
      checked:['reactions','local floor arming','music controls','start/stop recording','Whisper+Piper','three offline games','mobile overflow']},null,2));
  } finally {
    await browser.close();
  }
})().catch(e=>{console.error(e);process.exitCode=1});
