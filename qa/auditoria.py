"""QA do HTML autocontido. Requer Playwright e Google Chrome instalados."""
import json
import math
import os
from html.parser import HTMLParser
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
GAME = ROOT / 'A Corrida da Aposentadoria .html'
OUT = ROOT / 'qa' / 'prints'
OUT.mkdir(exist_ok=True)
RESULTS = {}
ERRORS = []

class Dependencias(HTMLParser):
    def __init__(self):
        super().__init__()
        self.externas = []
    def handle_starttag(self, tag, attrs):
        for nome, valor in attrs:
            if nome in ('src','href') and valor and not valor.startswith(('data:','#')):
                self.externas.append(valor)

parser = Dependencias()
parser.feed(GAME.read_text())
assert not parser.externas, parser.externas

def check(name, result=True):
    RESULTS[name] = result
    print(json.dumps({name: result}, ensure_ascii=False), flush=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)

    def fresh(size=(900, 600), seed=24, clock=True):
        context = browser.new_context(viewport={'width': size[0], 'height': size[1]}, has_touch=True)
        page = context.new_page()
        page.on('pageerror', lambda e: ERRORS.append(str(e)))
        page.on('console', lambda m: ERRORS.append(m.text) if m.type in ('error', 'warning') else None)
        page.add_init_script(f'''let s={seed}; Math.random=()=>{{s=(Math.imul(s,1664525)+1013904223)|0;return (s>>>0)/4294967296;}};''')
        if clock:
            page.clock.install()
        page.goto(GAME.as_uri())
        if clock:
            page.clock.fast_forward(50)
        else:
            page.wait_for_timeout(100)
        return context, page

    def work(page):
        page.evaluate('''() => {
          if(PORT) document.getElementById('btnP').dispatchEvent(new PointerEvent('pointerdown',{button:0,isPrimary:true,bubbles:true}));
          else { const r=cv.getBoundingClientRect(); cv.dispatchEvent(new MouseEvent('click',{clientX:r.left+775*r.width/W,clientY:r.top+550*r.height/H,bubbles:true})); }
        }''')

    def buy(page, i):
        page.evaluate('''i => {
          if(PORT) itensP[i].click(); else {const a=itemRect(i),r=cv.getBoundingClientRect(); cv.dispatchEvent(new MouseEvent('click',{clientX:r.left+(a.x+a.w/2)*r.width/W,clientY:r.top+(a.y+a.h/2)*r.height/H,bubbles:true}));}
        }''', i)
        page.clock.fast_forward(20)
        page.evaluate('''() => { if(V.popup) {if(PORT) document.getElementById('popOkP').click();else {const a=V.okRect,r=cv.getBoundingClientRect();cv.dispatchEvent(new MouseEvent('click',{clientX:r.left+(a.x+a.w/2)*r.width/W,clientY:r.top+(a.y+a.h/2)*r.height/H}));}} }''')

    # Matemática, valores inválidos e contratos dos upgrades.
    c, page = fresh()
    vals = page.evaluate('''() => [0,-1,NaN,Infinity,11,12,13,10000].map(x=>calcVitoria(x))''')
    assert all(1 <= v['meses'] <= 12 and v['idade'] >= 65 for v in vals)
    page.evaluate('trabalhar()')
    assert abs(page.evaluate('E.linha') - (100 + .3 + math.log(2)*.05)) < 1e-9
    page.evaluate('E.meses=200;E.linha=1000;comprarHora();V.popup=null')
    assert page.evaluate('E.velocidadeClique===1.2 && E.horaExtra && E.meses===150')
    page.evaluate('E.burnout=0;trabalhar()')
    assert abs(page.evaluate('E.burnout')-1.51)<1e-9
    page.evaluate('comprarCurso()')
    assert page.evaluate('V.calmoAte>agora() && Math.abs(E.meses-121.2)<.001')
    page.evaluate('comprarEmp();V.popup=null')
    assert abs(page.evaluate('E.meses')-111.2)<1e-9
    old = page.evaluate('E.linha')
    page.evaluate('comprarNegocio();V.popup=null;comprarNegocio()')
    assert abs(page.evaluate('E.linha')-old*1.15)<1e-9
    assert abs(page.evaluate('E.meses')-71.2)<1e-9
    page.evaluate('fimDeJogo(false)')
    before=page.evaluate('JSON.stringify(E)')
    page.evaluate('comprarCurso();comprarEmp();comprarHora();comprarNegocio();trabalhar();fimDeJogo(true)')
    assert page.evaluate('JSON.stringify(E)') == before
    check('matematica_e_4_upgrades')
    c.close()

    # Eventos com relógio acelerado, incluindo pausa de aba em uma janela ativa.
    c,page=fresh()
    page.evaluate('E.meses=100;eventoFator()');assert page.evaluate('E.meses')==75
    page.evaluate('eventoIntimacao()');assert page.evaluate('E.meses')==67
    page.evaluate('E.meses=1;eventoFator()');assert page.evaluate('E.meses===0&&!E.acabou')
    page.evaluate('eventoJanela();window.metaAntes=E.linha;trabalhar()');assert page.evaluate('E.linha===metaAntes')
    page.clock.fast_forward(4900);assert page.evaluate('E.travada')
    page.clock.fast_forward(150);assert page.evaluate('!E.travada')
    page.evaluate("window.hits=0;window.avisoOriginal=aviso;aviso=(...args)=>{hits++;avisoOriginal(...args)};proximoEvento=agora()+12000")
    page.clock.fast_forward(11900);assert page.evaluate('hits')==0
    page.clock.fast_forward(150);assert page.evaluate('hits')==1,page.evaluate('({hits,now:agora(),proximoEvento})')
    page.clock.fast_forward(12000);assert page.evaluate('hits')==2
    page.evaluate("Object.defineProperty(document,'hidden',{configurable:true,get:()=>window.qaOculta||false});eventoJanela();window.qaOculta=true;document.dispatchEvent(new Event('visibilitychange'));window.tempoAntes=agora();window.estadoAntes=JSON.stringify(E)")
    page.clock.fast_forward(60000)
    assert page.evaluate('agora()===tempoAntes && JSON.stringify(E)===estadoAntes')
    page.evaluate("window.qaOculta=false;document.dispatchEvent(new Event('visibilitychange'))")
    page.clock.fast_forward(4900);assert page.evaluate('E.travada')
    page.clock.fast_forward(150);assert page.evaluate('!E.travada')
    check('eventos_12s_janela_5s_pausa_aba')
    c.close()

    # Mouse, toque, teclado, rotação, mudo e marcas nos dois layouts.
    for size in [(900,600),(400,900)]:
        c,page=fresh(size)
        if size[0]<size[1]:
            page.locator('#btnP').tap()
            n=page.evaluate('E.cliques')
            page.locator('#btnP').click(button='right')
            assert page.evaluate('E.cliques')==n
            page.locator('#btnP').focus();page.keyboard.press('Enter')
            assert page.evaluate('E.cliques')==n+1
            page.evaluate('E.meses=30')
            page.locator('.itemP').nth(1).focus();page.keyboard.press('Enter')
            assert page.evaluate('E.meses===0 && E.cliques===2')
        else:
            page.mouse.click(775,550)
            assert page.evaluate('E.cliques')==1
        for _ in range(20):work(page)
        assert page.evaluate('M.length')==15
        page.clock.fast_forward(1550);assert page.evaluate('M.length')==0
        page.evaluate('E.meses=200;E.linha=1000')
        for i in [1,2,3,0]:buy(page,i)
        assert page.evaluate('E.horaExtra && E.negociou && E.meses===70')
        page.screenshot(path=str(OUT/f'layout-{size[0]}x{size[1]}.png'))
        for width,height in [(900,400),(400,900),(1600,900),(900,600)]:
            page.set_viewport_size({'width':width,'height':height});page.wait_for_timeout(80);page.clock.fast_forward(50)
            r=page.locator('#c').bounding_box();assert abs(r['width']/r['height']-1.5)<.01
            if width>height:
                m=page.locator('#mudo').bounding_box()
                assert abs(m['x']-(r['x']+648*r['width']/900))<1,{'viewport':[width,height],'mudo':m,'canvas':r}
        check(f'hitboxes_teclado_marcas_rotacao_{size[0]}x{size[1]}')
        c.close()

    # Partidas completas com eventos e relógio acelerado, sem alterar fórmulas.
    for size in [(900,600),(400,900)]:
        for modo in ['normal','burnout','todos_upgrades']:
            if os.environ.get('QA_CONTINUAR') and size==(900,600):
                continue
            sucesso=False
            seeds=[24,7,91] if modo=='todos_upgrades' else ([7,91,24] if modo=='normal' else [24])
            for seed in seeds:
                c,page=fresh(size,seed)
                comprados=set()
                for n in range(700):
                    if page.evaluate('E.acabou'):break
                    state=page.evaluate('({meses:E.meses,meta:E.linha,extra:E.horaExtra,travada:E.travada})')
                    if modo=='burnout' and state['meses']>=50 and not state['extra']:
                        buy(page,0)
                    if modo=='todos_upgrades':
                        for i,custo in [(2,10),(1,30),(3,40)]:
                            if i not in comprados and state['meses']>=custo:
                                buy(page,i);comprados.add(i);break
                        if len(comprados)==3 and not state['extra'] and state['meses']>=50 and state['meta']-state['meses']<1.3:
                            buy(page,0)
                    work(page)
                    page.clock.fast_forward(10 if modo=='burnout' else 200)
                result=page.evaluate('({fim:!!V.fim,vitoria:V.fim?.vitoria,cliques:E.cliques,burnout:E.burnout,horaExtra:E.horaExtra,negociou:E.negociou})')
                esperado=modo!='burnout'
                sucesso=result['fim'] and result['vitoria']==esperado and (modo!='todos_upgrades' or (result['horaExtra'] and len(comprados)==3))
                if sucesso:
                    page.clock.run_for(1200)
                    page.screenshot(path=str(OUT/f'{modo}-{size[0]}x{size[1]}.png'))
                    # Todos os botões de reinício devem funcionar após o atestado.
                    with page.expect_navigation(wait_until='load'):
                        if size[0]<size[1]:
                            page.evaluate("const r=$g('fimc').getBoundingClientRect(),a=V.fimBtn;$g('fimc').dispatchEvent(new MouseEvent('click',{clientX:r.left+a.x+100,clientY:r.top+a.y+20}))")
                        else:
                            a=page.evaluate('V.fimBtn');page.mouse.click(a['x']+100,a['y']+20)
                    assert page.evaluate('!E.acabou && E.cliques===0')
                    check(f'partida_{modo}_{size[0]}x{size[1]}',result)
                    c.close();break
                check(f'tentativa_{modo}_{size[0]}x{size[1]}_seed{seed}',result)
                c.close()
            assert sucesso,(size,modo,result)

    # Zero não é condição de derrota: testa zero legítimo e a apresentação defensiva.
    for progresso in ['0','NaN']:
        c,page=fresh((400,900))
        page.evaluate(f'E.meses={progresso};E.burnout=100;fimDeJogo(false)')
        assert '65 anos' in page.evaluate('V.fim.virada[0]')
        page.clock.run_for(1200)
        page.screenshot(path=str(OUT/f'derrota-{progresso}.png'))
        c.close()
    check('derrota_zero_e_NaN_65_anos')

    # Áudio real da API: um contexto, fila limitada e preferência após recarga.
    c,page=fresh(clock=False)
    assert page.evaluate('mudo && audioContext===null')
    page.locator('#mudo').click();assert page.evaluate('!mudo')
    page.evaluate('window.contextoInicial=audioContext;window.filaMax=0;for(let i=0;i<100;i++){somClique();somCompra();filaMax=Math.max(filaMax,ultimoSom-audioContext.currentTime)}')
    assert page.evaluate('audioContext===contextoInicial && filaMax<=.051')
    page.wait_for_timeout(150)
    page.evaluate('somEvento();somMoedas();somVitoria();somDerrota()')
    page.locator('#mudo').click();assert page.evaluate("mudo && localStorage.getItem('aposentadoria_mudo')==='true'")
    page.wait_for_timeout(1000);assert page.evaluate('fontesAudio.size')==0
    page.reload();page.mouse.click(775,550);assert page.evaluate('mudo')
    page.locator('#mudo').click();page.reload();assert page.evaluate('mudo && audioContext===null')
    page.mouse.click(775,550);assert page.evaluate('!mudo')
    check('audio_contexto_throttle_fontes_mudo_persistente')
    c.close()

    # 10 minutos simulados a 100 cliques/s, reiniciando o estado ao encerrar rodadas.
    c,page=fresh()
    max_p=max_m=0
    for segundo in range(600):
        counts=page.evaluate('''() => {for(let i=0;i<100;i++) {if(E.acabou){E.acabou=false;E.meses=0;E.linha=100;E.pib=0;E.burnout=0;V.fim=null;} trabalhar();} return [P.length,M.length];}''')
        max_p=max(max_p,counts[0]);max_m=max(max_m,counts[1])
        page.clock.fast_forward(1000)
    assert max_p<=200 and max_m<=15
    page.evaluate('E.acabou=true')
    page.clock.fast_forward(16000)
    assert page.evaluate('P.length===0 && M.length===0')
    check('carga_10min_simulados_60000_cliques',{'maxParticulas':max_p,'maxMarcas':max_m,'limpezaCompleta':True})
    c.close()

    c,page=fresh((400,900),clock=False)
    fps=page.evaluate('''() => new Promise(resolve=>{let start=performance.now(),n=0;function f(t){n++;if(t-start<3000)requestAnimationFrame(f);else resolve(n*1000/(t-start));}requestAnimationFrame(f);})''')
    check('fps_real_headless_portrait',round(fps,1))
    c.close()
    assert not ERRORS,ERRORS
    check('console_sem_erros_ou_warnings')
    (ROOT/'qa'/'resultado.json').write_text(json.dumps(RESULTS,ensure_ascii=False,indent=2)+'\n')
    browser.close()
