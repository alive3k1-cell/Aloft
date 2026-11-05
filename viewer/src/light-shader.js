export const LIGHT_GLSL=`
uniform float uTime,uMode,uMaster,uLevel,uWhite,uWaveDepth,uColorAmount,uChaseWidth,uPool,uPoolEffects;
uniform vec3 uRGB,uWhiteColor;
uniform vec4 uShow;
varying float vLightPhase;
varying float vNeonEnergy;
vec3 rgb2hsv(vec3 c){float high=max(c.r,max(c.g,c.b));float low=min(c.r,min(c.g,c.b));float delta=high-low;float hue=0.;if(delta>1.e-7){if(high==c.r)hue=(c.g-c.b)/delta;else if(high==c.g)hue=2.+(c.b-c.r)/delta;else hue=4.+(c.r-c.g)/delta;}return vec3(fract(hue/6.+1.),high>1.e-7?delta/high:0.,high);}
vec3 hsv2rgb(vec3 c){float h=fract(c.x)*6.;float sector=floor(h);float f=h-sector;float low=c.z*(1.-c.y);float falling=c.z*(1.-c.y*f);float rising=c.z*(1.-c.y*(1.-f));if(sector<1.)return vec3(c.z,rising,low);if(sector<2.)return vec3(falling,c.z,low);if(sector<3.)return vec3(low,c.z,rising);if(sector<4.)return vec3(low,falling,c.z);if(sector<5.)return vec3(rising,low,c.z);return vec3(c.z,low,falling);}
vec3 oneEffect(float mode,float p){
 float t=uTime/8.;float gain=1.;vec3 color=uRGB;
 bool fx=uPool<.5||uPoolEffects>.5;
 if(fx){
  if(mode>.5&&mode<2.5){vec3 h=rgb2hsv(uRGB);h.x+=.4*uColorAmount*sin(6.2831853*(t+(mode>1.5?p*.65:0.)));color=hsv2rgb(h);}
  if(mode>1.5&&mode<2.5)gain=1.-uWaveDepth*(1.-(.5+.5*sin(12.5663706*(p-t))));
  if(mode>2.5&&mode<3.5)gain=.08+.92*pow(max(0.,1.-abs(fract(p-t+.5)-.5)/uChaseWidth),2.);
  if(mode>3.5){float w=.5+.5*sin(6.2831853*(p*2.-t));vec3 h=rgb2hsv(uRGB);h.x+=.08*w;color=hsv2rgb(h);float sparks=pow(max(0.,sin(6.2831853*(p*31.-t*.7))),24.);color=mix(color,vec3(1.),sparks*.7);gain=.4+.6*pow(.5+.5*sin(6.2831853*(p*3.-t)),2.);}
 }
 return clamp(color+uWhite*uWhiteColor,0.,1.)*gain;
}
vec3 evaluateLight(){vec3 c;if(uMode<4.5)c=oneEffect(uMode,vLightPhase);else c=uShow.x*oneEffect(0.,vLightPhase)+uShow.y*oneEffect(1.,vLightPhase)+uShow.z*oneEffect(2.,vLightPhase)+uShow.w*oneEffect(3.,vLightPhase);return c*(26.*uMaster*uLevel*vNeonEnergy);}
`;
export function installLightShader(material,uniforms){
 material.onBeforeCompile=shader=>{
  Object.assign(shader.uniforms,uniforms);
  shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nattribute vec3 aNeonCenter;uniform float uPixelHeight;varying float vLightPhase;varying float vNeonEnergy;').replace('#include <begin_vertex>',`#include <begin_vertex>
vLightPhase=uv.x;
vec4 lineCenterView=modelViewMatrix*vec4(aNeonCenter,1.);
float depthFactor=projectionMatrix[3][3]<.5?max(.01,-lineCenterView.z):1.;
float pixelRadius=.009*uPixelHeight*projectionMatrix[1][1]/(2.*depthFactor);
float radiusScale=max(1.,.625/max(pixelRadius,.001));
transformed=aNeonCenter+(transformed-aNeonCenter)*radiusScale;
vNeonEnergy=1./radiusScale;
`);
  shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\n'+LIGHT_GLSL).replace('#include <emissivemap_fragment>','totalEmissiveRadiance=evaluateLight();');
 };
 material.customProgramCacheKey=()=> 'aloft-rgbw-v10';
}
