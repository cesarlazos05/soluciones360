from odoo import http
from odoo.http import request, Response


class SC360LandingController(http.Controller):

    @http.route('/landing', type='http', auth='public', website=False, csrf=False)
    def landing_page(self, **kwargs):
        html = self._build_landing_html()
        return Response(html, content_type='text/html; charset=utf-8', status=200)

    def _build_landing_html(self):
        return '''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>SC360 — Soluciones Constructivas 360</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=DM+Sans:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  :root {
    --black: #0a0a0a;
    --white: #fafafa;
    --gray-50: #f5f5f5;
    --gray-100: #e8e8e8;
    --gray-200: #d4d4d4;
    --gray-400: #a3a3a3;
    --gray-500: #737373;
    --gray-600: #525252;
    --gray-800: #262626;
    --gray-900: #171717;
    --teal: #0f766e;
    --teal-light: #14b8a6;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: 'Inter', -apple-system, sans-serif;
    background: var(--white);
    color: var(--black);
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
  }
  a { text-decoration: none; transition: opacity 0.2s; }
  a:hover { opacity: 0.85; }
</style>
</head>
<body>

<!-- NAV -->
<nav style="display: flex; justify-content: space-between; align-items: center; padding: 24px 48px; background: var(--black); position: sticky; top: 0; z-index: 100;">
  <a href="/landing">
    <svg viewBox="0 0 400 80" width="120" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 58.5C8 58.5 14.5 64 27 64C40.5 64 47 57 47 49.5C47 42 41 38.5 28.5 35.5C16 32.5 8 28.5 8 18C8 7.5 17 1 29 1C41 1 48 7 48 7L43.5 14.5C43.5 14.5 37.5 9 29 9C20.5 9 16 14 16 19C16 24 21.5 26.5 33 29.5C44.5 32.5 55 37.5 55 49.5C55 61.5 44.5 72 27 72C9.5 72 2.5 63.5 2.5 63.5L8 58.5Z" fill="#fafafa"/>
      <path d="M100 55C100 55 92 64 78 64C62 64 52 51.5 52 36.5C52 21.5 63 8 80 8C92 8 99 15 99 15L94.5 22.5C94.5 22.5 89 17 80 17C69 17 61 26 61 36.5C61 47 68.5 56 79.5 56C90.5 56 96 48 96 48L100 55Z" fill="#fafafa"/>
      <path d="M140 36C148 33 152 27.5 152 21C152 12 145 5 133 5C122 5 115 12 115 12L119.5 19C119.5 19 125 13.5 133 13.5C139 13.5 143.5 17 143.5 22C143.5 27 139.5 31 131 31H126V39H131.5C141 39 145.5 43.5 145.5 49.5C145.5 55.5 140.5 59 133 59C123 59 116.5 52 116.5 52L112 59C112 59 120 67 133.5 67C148 67 154.5 58 154.5 49.5C154.5 41 148.5 37.5 140 36Z" fill="#fafafa"/>
      <path d="M186 5L178 16C173 23 168 32.5 168 43.5C168 56 176 67 190 67C202.5 67 210 57.5 210 47C210 37 202.5 29.5 192 29.5C185 29.5 180 33 177.5 36C178 29 182 21 187.5 14L196 5H186ZM190.5 37.5C198 37.5 202 42.5 202 47.5C202 53 198 59 190 59C182 59 177 53 177 46C177 43 178 40.5 180 38.5C182.5 37.5 186 37.5 190.5 37.5Z" fill="#fafafa"/>
      <path d="M240 67C256 67 266 54 266 36C266 18 256 5 240 5C224 5 214 18 214 36C214 54 224 67 240 67ZM240 59C230 59 223 50 223 36C223 22 230 13 240 13C250 13 257 22 257 36C257 50 250 59 240 59Z" fill="#fafafa"/>
      <rect x="280" y="30" width="40" height="4" rx="2" fill="#14b8a6"/>
    </svg>
  </a>
  <div style="display: flex; gap: 40px; align-items: center;">
    <a href="#servicios" style="font-size: 13px; color: var(--gray-400); text-decoration: none; letter-spacing: 0.5px; font-weight: 400;">Servicios</a>
    <a href="#proyectos" style="font-size: 13px; color: var(--gray-400); text-decoration: none; letter-spacing: 0.5px; font-weight: 400;">Proyectos</a>
    <a href="#nosotros" style="font-size: 13px; color: var(--gray-400); text-decoration: none; letter-spacing: 0.5px; font-weight: 400;">Nosotros</a>
    <a href="#contacto" style="font-size: 13px; background: var(--teal); color: white; text-decoration: none; padding: 10px 24px; border-radius: 6px; font-weight: 500; letter-spacing: 0.3px;">Contacto</a>
  </div>
</nav>

<!-- HERO -->
<div style="background: var(--black); padding: 120px 80px 140px; position: relative; overflow: hidden;">
  <div style="position: absolute; top: -100px; right: -100px; width: 500px; height: 500px; border: 1px solid rgba(255,255,255,0.03); border-radius: 50%;"></div>
  <div style="position: absolute; bottom: -200px; left: 10%; width: 600px; height: 600px; background: var(--teal); opacity: 0.04; border-radius: 50%; filter: blur(80px);"></div>
  <div style="position: relative; z-index: 1; max-width: 800px;">
    <span style="font-size: 11px; letter-spacing: 4px; text-transform: uppercase; color: var(--teal-light); font-weight: 500;">Construccion integral</span>
    <h1 style="font-family: 'DM Sans', sans-serif; font-size: 72px; font-weight: 700; line-height: 1.05; letter-spacing: -3px; color: var(--white); margin-top: 24px;">Construimos lo que<br>otros solo<br><span style="color: var(--teal-light);">imaginan.</span></h1>
    <p style="font-size: 19px; line-height: 1.7; color: var(--gray-400); max-width: 520px; margin-top: 32px;">Residencial, comercial y obra civil. Mas de 15 anos transformando visiones en estructuras que perduran.</p>
    <div style="display: flex; gap: 16px; margin-top: 48px;">
      <a href="#contacto" style="font-size: 15px; background: var(--teal); color: white; text-decoration: none; padding: 16px 36px; border-radius: 8px; font-weight: 600; letter-spacing: 0.3px; display: inline-block;">Solicitar cotizacion</a>
      <a href="#proyectos" style="font-size: 15px; background: transparent; color: var(--white); text-decoration: none; padding: 16px 36px; border-radius: 8px; font-weight: 500; border: 1px solid rgba(255,255,255,0.15); display: inline-block;">Ver proyectos</a>
    </div>
  </div>
  <div style="display: flex; gap: 80px; margin-top: 100px; position: relative; z-index: 1; padding-top: 48px; border-top: 1px solid rgba(255,255,255,0.08);">
    <div>
      <div style="font-family: 'DM Sans', sans-serif; font-size: 48px; font-weight: 700; color: var(--white); letter-spacing: -2px;">150<span style="color: var(--teal-light);">+</span></div>
      <div style="font-size: 13px; color: var(--gray-500); margin-top: 4px; letter-spacing: 0.5px;">Proyectos entregados</div>
    </div>
    <div>
      <div style="font-family: 'DM Sans', sans-serif; font-size: 48px; font-weight: 700; color: var(--white); letter-spacing: -2px;">15</div>
      <div style="font-size: 13px; color: var(--gray-500); margin-top: 4px; letter-spacing: 0.5px;">Anos de experiencia</div>
    </div>
    <div>
      <div style="font-family: 'DM Sans', sans-serif; font-size: 48px; font-weight: 700; color: var(--white); letter-spacing: -2px;">98<span style="color: var(--teal-light);">%</span></div>
      <div style="font-size: 13px; color: var(--gray-500); margin-top: 4px; letter-spacing: 0.5px;">Clientes satisfechos</div>
    </div>
    <div>
      <div style="font-family: 'DM Sans', sans-serif; font-size: 48px; font-weight: 700; color: var(--white); letter-spacing: -2px;">3</div>
      <div style="font-size: 13px; color: var(--gray-500); margin-top: 4px; letter-spacing: 0.5px;">Sectores de especialidad</div>
    </div>
  </div>
</div>

<!-- SERVICIOS -->
<div id="servicios" style="padding: 120px 80px; background: var(--white);">
  <span style="font-size: 11px; font-weight: 500; letter-spacing: 3px; text-transform: uppercase; color: var(--gray-400);">Servicios</span>
  <h2 style="font-family: 'DM Sans', sans-serif; font-size: 44px; font-weight: 500; letter-spacing: -1.5px; color: var(--gray-900); margin-top: 24px; margin-bottom: 64px; max-width: 500px; line-height: 1.15;">Lo que hacemos,<br>lo hacemos bien.</h2>
  <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 32px;">
    <div style="padding: 48px 40px; background: var(--gray-50); border-radius: 16px; display: flex; flex-direction: column; gap: 24px;">
      <div style="width: 48px; height: 48px; background: var(--black); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
        <svg viewBox="0 0 24 24" width="22" fill="none" stroke="#14b8a6" stroke-width="1.5"><path d="M3 21h18M5 21V7l7-4 7 4v14M9 21v-6h6v6"/></svg>
      </div>
      <h3 style="font-family: 'DM Sans', sans-serif; font-size: 22px; font-weight: 600; color: var(--gray-900); letter-spacing: -0.5px;">Residencial</h3>
      <p style="font-size: 15px; line-height: 1.65; color: var(--gray-500);">Casas, departamentos y desarrollos habitacionales. Desde el diseno arquitectonico hasta la entrega de llaves.</p>
      <div style="margin-top: auto; padding-top: 24px; border-top: 1px solid var(--gray-200);">
        <span style="font-size: 12px; color: var(--teal); font-weight: 500; letter-spacing: 0.5px;">Casas &middot; Departamentos &middot; Fraccionamientos</span>
      </div>
    </div>
    <div style="padding: 48px 40px; background: var(--gray-50); border-radius: 16px; display: flex; flex-direction: column; gap: 24px;">
      <div style="width: 48px; height: 48px; background: var(--black); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
        <svg viewBox="0 0 24 24" width="22" fill="none" stroke="#14b8a6" stroke-width="1.5"><path d="M2 20h20M4 20V8h6v12M10 20V4h10v16M14 8h2M14 12h2M14 16h2"/></svg>
      </div>
      <h3 style="font-family: 'DM Sans', sans-serif; font-size: 22px; font-weight: 600; color: var(--gray-900); letter-spacing: -0.5px;">Comercial e Industrial</h3>
      <p style="font-size: 15px; line-height: 1.65; color: var(--gray-500);">Naves industriales, plazas comerciales y edificios de oficinas. Estructuras que optimizan operacion y rentabilidad.</p>
      <div style="margin-top: auto; padding-top: 24px; border-top: 1px solid var(--gray-200);">
        <span style="font-size: 12px; color: var(--teal); font-weight: 500; letter-spacing: 0.5px;">Naves &middot; Plazas &middot; Oficinas</span>
      </div>
    </div>
    <div style="padding: 48px 40px; background: var(--gray-50); border-radius: 16px; display: flex; flex-direction: column; gap: 24px;">
      <div style="width: 48px; height: 48px; background: var(--black); border-radius: 10px; display: flex; align-items: center; justify-content: center;">
        <svg viewBox="0 0 24 24" width="22" fill="none" stroke="#14b8a6" stroke-width="1.5"><path d="M2 18h20M4 18l2-12h12l2 12M8 6h8M12 2v4"/></svg>
      </div>
      <h3 style="font-family: 'DM Sans', sans-serif; font-size: 22px; font-weight: 600; color: var(--gray-900); letter-spacing: -0.5px;">Obra Civil</h3>
      <p style="font-size: 15px; line-height: 1.65; color: var(--gray-500);">Infraestructura publica y privada. Caminos, puentes, urbanizacion y proyectos de gran escala con estandares rigurosos.</p>
      <div style="margin-top: auto; padding-top: 24px; border-top: 1px solid var(--gray-200);">
        <span style="font-size: 12px; color: var(--teal); font-weight: 500; letter-spacing: 0.5px;">Infraestructura &middot; Urbanizacion &middot; Puentes</span>
      </div>
    </div>
  </div>
</div>

<!-- PROCESO -->
<div id="nosotros" style="padding: 120px 80px; background: var(--gray-50); border-top: 1px solid var(--gray-100);">
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 100px; align-items: center;">
    <div>
      <span style="font-size: 11px; font-weight: 500; letter-spacing: 3px; text-transform: uppercase; color: var(--gray-400);">Proceso</span>
      <h2 style="font-family: 'DM Sans', sans-serif; font-size: 40px; font-weight: 500; letter-spacing: -1.5px; color: var(--gray-900); margin-top: 24px; margin-bottom: 48px; line-height: 1.15;">De la vision<br>a la realidad.</h2>
      <div style="display: flex; flex-direction: column; gap: 0;">
        <div style="display: flex; gap: 24px; padding: 28px 0; border-bottom: 1px solid var(--gray-200);">
          <div style="font-family: 'DM Sans', sans-serif; font-size: 14px; font-weight: 700; color: var(--teal); min-width: 28px;">01</div>
          <div>
            <div style="font-family: 'DM Sans', sans-serif; font-size: 17px; font-weight: 600; color: var(--gray-900); margin-bottom: 6px;">Consulta inicial</div>
            <div style="font-size: 14px; color: var(--gray-500); line-height: 1.6;">Entendemos tu proyecto, tus tiempos y tu presupuesto. Sin compromiso.</div>
          </div>
        </div>
        <div style="display: flex; gap: 24px; padding: 28px 0; border-bottom: 1px solid var(--gray-200);">
          <div style="font-family: 'DM Sans', sans-serif; font-size: 14px; font-weight: 700; color: var(--teal); min-width: 28px;">02</div>
          <div>
            <div style="font-family: 'DM Sans', sans-serif; font-size: 17px; font-weight: 600; color: var(--gray-900); margin-bottom: 6px;">Diseno y planeacion</div>
            <div style="font-size: 14px; color: var(--gray-500); line-height: 1.6;">Arquitectura, ingenieria estructural y presupuesto detallado.</div>
          </div>
        </div>
        <div style="display: flex; gap: 24px; padding: 28px 0; border-bottom: 1px solid var(--gray-200);">
          <div style="font-family: 'DM Sans', sans-serif; font-size: 14px; font-weight: 700; color: var(--teal); min-width: 28px;">03</div>
          <div>
            <div style="font-family: 'DM Sans', sans-serif; font-size: 17px; font-weight: 600; color: var(--gray-900); margin-bottom: 6px;">Construccion</div>
            <div style="font-size: 14px; color: var(--gray-500); line-height: 1.6;">Ejecucion con supervision constante. Reportes de avance semanales.</div>
          </div>
        </div>
        <div style="display: flex; gap: 24px; padding: 28px 0;">
          <div style="font-family: 'DM Sans', sans-serif; font-size: 14px; font-weight: 700; color: var(--teal); min-width: 28px;">04</div>
          <div>
            <div style="font-family: 'DM Sans', sans-serif; font-size: 17px; font-weight: 600; color: var(--gray-900); margin-bottom: 6px;">Entrega y garantia</div>
            <div style="font-size: 14px; color: var(--gray-500); line-height: 1.6;">Inspeccion final, documentacion completa y garantia por escrito.</div>
          </div>
        </div>
      </div>
    </div>
    <div style="background: var(--black); border-radius: 16px; padding: 64px; display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 500px; position: relative; overflow: hidden;">
      <div style="position: absolute; top: -50%; right: -30%; width: 400px; height: 400px; border: 1px solid rgba(255,255,255,0.04); border-radius: 50%;"></div>
      <svg viewBox="0 0 80 80" width="80" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="8" y="8" width="64" height="64" rx="4" stroke="#fafafa" stroke-width="2.5" fill="none"/>
        <text x="40" y="48" text-anchor="middle" font-family="DM Sans, sans-serif" font-weight="700" font-size="28" fill="#fafafa" letter-spacing="-1">SC</text>
        <rect x="28" y="56" width="24" height="2.5" rx="1.25" fill="#14b8a6"/>
      </svg>
      <div style="margin-top: 40px; text-align: center;">
        <div style="font-family: 'DM Sans', sans-serif; font-size: 24px; font-weight: 600; color: var(--white); letter-spacing: -0.5px;">Calidad sin<br>negociacion.</div>
        <div style="font-size: 13px; color: var(--gray-500); margin-top: 16px; line-height: 1.6; max-width: 260px;">Cada proyecto pasa por control de calidad en cada fase. No entregamos hasta que este perfecto.</div>
      </div>
      <div style="position: absolute; bottom: 40px; left: 40px; right: 40px; display: flex; justify-content: space-between;">
        <span style="font-size: 10px; letter-spacing: 2px; color: var(--gray-600); text-transform: uppercase;">ISO 9001</span>
        <span style="font-size: 10px; letter-spacing: 2px; color: var(--gray-600); text-transform: uppercase;">NOM Compliant</span>
      </div>
    </div>
  </div>
</div>

<!-- PROYECTOS -->
<div id="proyectos" style="padding: 120px 80px; background: var(--white);">
  <span style="font-size: 11px; font-weight: 500; letter-spacing: 3px; text-transform: uppercase; color: var(--gray-400);">Proyectos</span>
  <div style="display: flex; justify-content: space-between; align-items: flex-end; margin-top: 24px; margin-bottom: 64px;">
    <h2 style="font-family: 'DM Sans', sans-serif; font-size: 44px; font-weight: 500; letter-spacing: -1.5px; color: var(--gray-900); line-height: 1.15;">Trabajo reciente.</h2>
    <a href="#" style="font-size: 13px; color: var(--teal); text-decoration: none; font-weight: 500; letter-spacing: 0.5px; border-bottom: 1px solid var(--teal); padding-bottom: 2px;">Ver todos los proyectos</a>
  </div>
  <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 32px;">
    <div style="border-radius: 16px; overflow: hidden; background: var(--gray-50); aspect-ratio: 4/3; display: flex; flex-direction: column; justify-content: flex-end; padding: 40px; position: relative;">
      <div style="position: absolute; inset: 0; background: linear-gradient(135deg, #1a1a2e 0%, #0f766e 100%); opacity: 0.08;"></div>
      <div style="position: absolute; top: 24px; right: 24px; background: var(--white); padding: 6px 14px; border-radius: 20px; font-size: 11px; color: var(--gray-600); font-weight: 500;">Residencial</div>
      <div style="position: relative; z-index: 1;">
        <div style="font-family: 'DM Sans', sans-serif; font-size: 11px; color: var(--teal); font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px;">2025</div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 26px; font-weight: 600; color: var(--gray-900); letter-spacing: -0.5px;">Residencial Los Alamos</div>
        <div style="font-size: 14px; color: var(--gray-500); margin-top: 8px;">48 viviendas &middot; Monterrey, N.L.</div>
      </div>
    </div>
    <div style="border-radius: 16px; overflow: hidden; background: var(--gray-50); aspect-ratio: 4/3; display: flex; flex-direction: column; justify-content: flex-end; padding: 40px; position: relative;">
      <div style="position: absolute; inset: 0; background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); opacity: 0.06;"></div>
      <div style="position: absolute; top: 24px; right: 24px; background: var(--white); padding: 6px 14px; border-radius: 20px; font-size: 11px; color: var(--gray-600); font-weight: 500;">Comercial</div>
      <div style="position: relative; z-index: 1;">
        <div style="font-family: 'DM Sans', sans-serif; font-size: 11px; color: var(--teal); font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px;">2024</div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 26px; font-weight: 600; color: var(--gray-900); letter-spacing: -0.5px;">Plaza Comercial Valle</div>
        <div style="font-size: 14px; color: var(--gray-500); margin-top: 8px;">12,000 m&sup2; &middot; Guadalajara, Jal.</div>
      </div>
    </div>
    <div style="border-radius: 16px; overflow: hidden; background: var(--gray-50); aspect-ratio: 4/3; display: flex; flex-direction: column; justify-content: flex-end; padding: 40px; position: relative;">
      <div style="position: absolute; inset: 0; background: linear-gradient(135deg, #0f766e 0%, #14b8a6 100%); opacity: 0.06;"></div>
      <div style="position: absolute; top: 24px; right: 24px; background: var(--white); padding: 6px 14px; border-radius: 20px; font-size: 11px; color: var(--gray-600); font-weight: 500;">Obra Civil</div>
      <div style="position: relative; z-index: 1;">
        <div style="font-family: 'DM Sans', sans-serif; font-size: 11px; color: var(--teal); font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px;">2024</div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 26px; font-weight: 600; color: var(--gray-900); letter-spacing: -0.5px;">Vialidad Metropolitana Norte</div>
        <div style="font-size: 14px; color: var(--gray-500); margin-top: 8px;">3.2 km &middot; Zona Metropolitana</div>
      </div>
    </div>
    <div style="border-radius: 16px; overflow: hidden; background: var(--gray-50); aspect-ratio: 4/3; display: flex; flex-direction: column; justify-content: flex-end; padding: 40px; position: relative;">
      <div style="position: absolute; inset: 0; background: linear-gradient(135deg, #1a1a2e 0%, #0a0a0a 100%); opacity: 0.05;"></div>
      <div style="position: absolute; top: 24px; right: 24px; background: var(--white); padding: 6px 14px; border-radius: 20px; font-size: 11px; color: var(--gray-600); font-weight: 500;">Industrial</div>
      <div style="position: relative; z-index: 1;">
        <div style="font-family: 'DM Sans', sans-serif; font-size: 11px; color: var(--teal); font-weight: 600; letter-spacing: 1px; text-transform: uppercase; margin-bottom: 8px;">2023</div>
        <div style="font-family: 'DM Sans', sans-serif; font-size: 26px; font-weight: 600; color: var(--gray-900); letter-spacing: -0.5px;">Nave Industrial Apodaca</div>
        <div style="font-size: 14px; color: var(--gray-500); margin-top: 8px;">8,500 m&sup2; &middot; Apodaca, N.L.</div>
      </div>
    </div>
  </div>
</div>

<!-- TESTIMONIAL -->
<div style="padding: 120px 80px; background: var(--black); text-align: center;">
  <div style="max-width: 700px; margin: 0 auto;">
    <div style="width: 48px; height: 3px; background: var(--teal); margin: 0 auto 48px; border-radius: 2px;"></div>
    <blockquote style="font-family: 'DM Sans', sans-serif; font-size: 28px; font-weight: 400; color: var(--white); line-height: 1.5; letter-spacing: -0.5px; font-style: normal; border: none; margin: 0; padding: 0;">
      "Contratamos a SC360 para nuestra nave industrial y la entregaron antes de plazo, sin un solo cambio de orden. Es raro encontrar ese nivel de profesionalismo."
    </blockquote>
    <div style="margin-top: 40px;">
      <div style="font-family: 'DM Sans', sans-serif; font-size: 15px; font-weight: 600; color: var(--white);">Roberto Mendoza</div>
      <div style="font-size: 13px; color: var(--gray-500); margin-top: 4px;">Director de Operaciones, Grupo Logistico del Norte</div>
    </div>
  </div>
</div>

<!-- CTA -->
<div id="contacto" style="padding: 120px 80px; background: var(--white); text-align: center;">
  <div style="max-width: 600px; margin: 0 auto;">
    <h2 style="font-family: 'DM Sans', sans-serif; font-size: 48px; font-weight: 500; letter-spacing: -2px; color: var(--gray-900); line-height: 1.1;">Listo para<br>construir?</h2>
    <p style="font-size: 17px; color: var(--gray-500); margin-top: 24px; line-height: 1.7;">Cuentanos sobre tu proyecto. La primera consulta es sin costo y sin compromiso.</p>
    <div style="display: flex; gap: 16px; justify-content: center; margin-top: 48px;">
      <a href="/contacto" style="font-size: 15px; background: var(--black); color: white; text-decoration: none; padding: 18px 40px; border-radius: 8px; font-weight: 600; letter-spacing: 0.3px; display: inline-block;">Agendar consulta gratuita</a>
      <a href="https://wa.me/521234567890" style="font-size: 15px; background: transparent; color: var(--gray-900); text-decoration: none; padding: 18px 40px; border-radius: 8px; font-weight: 500; border: 1px solid var(--gray-200); display: inline-block;">WhatsApp directo</a>
    </div>
    <div style="margin-top: 40px; font-size: 13px; color: var(--gray-400);">
      +52 (55) 1234 5678 &middot; contacto@sc360.mx
    </div>
  </div>
</div>

<!-- FOOTER -->
<div style="padding: 48px 80px; background: var(--black); display: flex; justify-content: space-between; align-items: center; border-top: 1px solid rgba(255,255,255,0.06);">
  <a href="/landing">
    <svg viewBox="0 0 400 80" width="90" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path d="M8 58.5C8 58.5 14.5 64 27 64C40.5 64 47 57 47 49.5C47 42 41 38.5 28.5 35.5C16 32.5 8 28.5 8 18C8 7.5 17 1 29 1C41 1 48 7 48 7L43.5 14.5C43.5 14.5 37.5 9 29 9C20.5 9 16 14 16 19C16 24 21.5 26.5 33 29.5C44.5 32.5 55 37.5 55 49.5C55 61.5 44.5 72 27 72C9.5 72 2.5 63.5 2.5 63.5L8 58.5Z" fill="#fafafa"/>
      <path d="M100 55C100 55 92 64 78 64C62 64 52 51.5 52 36.5C52 21.5 63 8 80 8C92 8 99 15 99 15L94.5 22.5C94.5 22.5 89 17 80 17C69 17 61 26 61 36.5C61 47 68.5 56 79.5 56C90.5 56 96 48 96 48L100 55Z" fill="#fafafa"/>
      <path d="M140 36C148 33 152 27.5 152 21C152 12 145 5 133 5C122 5 115 12 115 12L119.5 19C119.5 19 125 13.5 133 13.5C139 13.5 143.5 17 143.5 22C143.5 27 139.5 31 131 31H126V39H131.5C141 39 145.5 43.5 145.5 49.5C145.5 55.5 140.5 59 133 59C123 59 116.5 52 116.5 52L112 59C112 59 120 67 133.5 67C148 67 154.5 58 154.5 49.5C154.5 41 148.5 37.5 140 36Z" fill="#fafafa"/>
      <path d="M186 5L178 16C173 23 168 32.5 168 43.5C168 56 176 67 190 67C202.5 67 210 57.5 210 47C210 37 202.5 29.5 192 29.5C185 29.5 180 33 177.5 36C178 29 182 21 187.5 14L196 5H186ZM190.5 37.5C198 37.5 202 42.5 202 47.5C202 53 198 59 190 59C182 59 177 53 177 46C177 43 178 40.5 180 38.5C182.5 37.5 186 37.5 190.5 37.5Z" fill="#fafafa"/>
      <path d="M240 67C256 67 266 54 266 36C266 18 256 5 240 5C224 5 214 18 214 36C214 54 224 67 240 67ZM240 59C230 59 223 50 223 36C223 22 230 13 240 13C250 13 257 22 257 36C257 50 250 59 240 59Z" fill="#fafafa"/>
      <rect x="280" y="30" width="40" height="4" rx="2" fill="#14b8a6"/>
    </svg>
  </a>
  <div style="display: flex; gap: 32px;">
    <span style="font-size: 12px; color: var(--gray-600);">Servicios</span>
    <span style="font-size: 12px; color: var(--gray-600);">Proyectos</span>
    <span style="font-size: 12px; color: var(--gray-600);">Nosotros</span>
    <span style="font-size: 12px; color: var(--gray-600);">Contacto</span>
  </div>
  <span style="font-size: 11px; color: var(--gray-600);">&copy; 2026 SC360. Todos los derechos reservados.</span>
</div>

</body>
</html>'''
