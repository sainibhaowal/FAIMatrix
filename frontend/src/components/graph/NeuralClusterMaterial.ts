import * as THREE from 'three';

/**
 * Neural Cluster Material
 * 
 * Custom shader material for the radial cluster particle system.
 * Implements a soft, bioluminescent glow with cyan/violet gradients.
 */

export const NeuralClusterMaterial = new THREE.ShaderMaterial({
  uniforms: {
    uTime: { value: 0 },
    uColorCenter: { value: new THREE.Color('#22d3ee') }, // Cyan 400
    uColorEdge: { value: new THREE.Color('#8b5cf6') },   // Violet 500
    uOpacity: { value: 0.8 }
  },
  vertexShader: `
    varying float vDistance;
    varying float vAlpha;
    uniform float uTime;

    void main() {
      // Position relative to cluster center
      vDistance = length(position);
      
      // Stronger pulsing effect based on distance and time
      float pulse = sin(uTime * 3.0 + vDistance * 5.0) * 0.15 + 0.95;
      
      vec4 mvPosition = modelViewMatrix * vec4(position * pulse, 1.0);
      
      // LARGER point size based on distance from center and camera distance
      // Base size increased from 4.0 to 12.0
      gl_PointSize = (12.0 * (1.8 - vDistance)) * (400.0 / -mvPosition.z);
      
      // Soften the edges more gradually
      vAlpha = smoothstep(1.5, 0.0, vDistance);
      gl_Position = projectionMatrix * mvPosition;
    }
  `,
  fragmentShader: `
    uniform vec3 uColorCenter;
    uniform vec3 uColorEdge;
    uniform float uOpacity;
    varying float vDistance;
    varying float vAlpha;

    void main() {
      // Circular particle shape
      float r = length(gl_PointCoord - vec2(0.5));
      if (r > 0.5) discard;
      
      // Radial color gradient - more towards center
      vec3 color = mix(uColorCenter, uColorEdge, vDistance * 0.8);
      
      // Soft edge alpha - more glowing
      float strength = pow(0.5 - r, 1.2) * 5.0;
      gl_FragColor = vec4(color, strength * vAlpha * uOpacity);
    }
  `,
  transparent: true,
  blending: THREE.AdditiveBlending,
  depthWrite: false,
});
