import * as THREE from 'three';
import { NeuralClusterMaterial } from './NeuralClusterMaterial';

/**
 * Neural Cluster Geometry
 * 
 * Generates a procedural particle cluster for a single FIG node.
 * Uses a radial distribution to create a "Neural Galaxy" effect.
 */

export class NeuralClusterGeometry {
  static createCluster(node: any): THREE.Group {
    const group = new THREE.Group();
    
    // Determine cluster density and scale based on node metadata
    const novelty = node.novelty ?? 0.5;
    const importance = node.importance ?? 0.5;
    
    // Increased particle density
    const particleCount = Math.floor(400 + importance * 600);
    const radius = 1.0 + novelty * 0.5;
    
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(particleCount * 3);
    
    for (let i = 0; i < particleCount; i++) {
        // Spherical distribution with bias towards center
        const theta = Math.random() * Math.PI * 2;
        const phi = Math.acos(2 * Math.random() - 1);
        
        // Distribution with a slight "shell" feel at the edge
        const r = radius * (0.3 + 0.7 * Math.pow(Math.random(), 0.5));
        
        const x = r * Math.sin(phi) * Math.cos(theta);
        const y = r * Math.sin(phi) * Math.sin(theta);
        const z = r * Math.cos(phi);
        
        positions[i * 3] = x;
        positions[i * 3 + 1] = y;
        positions[i * 3 + 2] = z;
    }
    
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    
    // Create material clone per node to allow individual animation/color if needed
    const mat = NeuralClusterMaterial.clone();
    
    // Vary the pulse phase slightly per node
    mat.uniforms.uTime.value = Math.random() * 100;
    
    // FAIM-aware node coloring based on level and flags
    const flags = node.evolution_flags ?? node.flags ?? [];
    const isEmergent = flags.includes('emergent') || flags.includes('synthesized') || novelty > 0.7;
    const isMerged = flags.includes('merged') || node.merged;
    const isPruned = flags.includes('pruned') || node.pruned;
    const level = node.level ?? 0;
    
    // Level-based color gradients (fractal hierarchy visualization)
    // Level 0 (raw atoms) = Cyan
    // Level 1 = Teal
    // Level 2 = Purple
    // Level 3+ = Deep violet
    const levelColors: [string, string][] = [
      ['#22d3ee', '#06b6d4'], // Level 0: Cyan
      ['#14b8a6', '#0d9488'], // Level 1: Teal
      ['#a78bfa', '#8b5cf6'], // Level 2: Purple
      ['#c084fc', '#9333ea'], // Level 3+: Deep violet
    ];
    
    const colorIdx = Math.min(level, levelColors.length - 1);
    const [centerColor, edgeColor] = levelColors[colorIdx];
    
    mat.uniforms.uColorCenter.value.set(centerColor);
    mat.uniforms.uColorEdge.value.set(edgeColor);
    
    // Override with special state colors
    if (isEmergent) {
      mat.uniforms.uColorCenter.value.set('#fbbf24'); // Gold
      mat.uniforms.uColorEdge.value.set('#ea580c');   // Orange 600
    } else if (isMerged) {
      mat.uniforms.uColorCenter.value.set('#60a5fa'); // Blue 400
      mat.uniforms.uColorEdge.value.set('#2563eb');   // Blue 600
    } else if (isPruned) {
      mat.uniforms.uColorCenter.value.set('#f87171'); // Red 400
      mat.uniforms.uColorEdge.value.set('#dc2626');   // Red 600
    }
    
    const points = new THREE.Points(geometry, mat);
    group.add(points);
    
    // Add a core glow (small bright sphere at center)
    const coreGeom = new THREE.SphereGeometry(0.15, 24, 24);
    const coreMat = new THREE.MeshBasicMaterial({
      color: mat.uniforms.uColorCenter.value,
      transparent: true,
      opacity: 1.0,
      blending: THREE.AdditiveBlending
    });
    const coreMesh = new THREE.Mesh(coreGeom, coreMat);
    group.add(coreMesh);

    // Add a secondary glowing shell (Aura)
    const auraGeom = new THREE.SphereGeometry(0.25, 24, 24);
    const auraMat = new THREE.MeshBasicMaterial({
      color: mat.uniforms.uColorEdge.value,
      transparent: true,
      opacity: 0.3,
      blending: THREE.AdditiveBlending
    });
    const auraMesh = new THREE.Mesh(auraGeom, auraMat);
    group.add(auraMesh);
    
    // Store metadata for animation logic in the rendering loop
    group.userData = { 
        baseScale: new THREE.Vector3(1, 1, 1),
        pulseSpeed: 0.8 + Math.random() * 0.4,
        phase: Math.random() * Math.PI * 2
    };
    
    return group;
  }
}
