"use client";

import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Bone, BoneFracture, Box, Layers, Rotate3d, RotateCw, Sparkles } from "lucide-react";

import { useTheme } from "next-themes";

export interface WorkflowSceneObject {
  name: string;
  primitiveType: string;
  dimensions: [number, number, number];
  location: [number, number, number];
  rotation?: [number, number, number];
  materialName?: string;
  modifiers?: string[];
}

interface ThreeViewportProps {
  assetSpec?: {
    asset_type?: string;
    dimensions?: { width: number; depth: number; height: number };
  };
  sceneObjects?: WorkflowSceneObject[];
  wireframeMode?: boolean;
  selectedObjectName?: string | null;
  onObjectSelect?: (name: string | null) => void;
}

function createGeometry(object: WorkflowSceneObject) {
  const [w, d, h] = object.dimensions;
  const type = object.primitiveType;

  if (type === "cylinder") return new THREE.CylinderGeometry(w / 2, d / 2, h, 32);
  if (type === "uv_sphere" || type === "sphere") return new THREE.SphereGeometry(Math.max(w, d, h) / 2, 32, 16);
  if (type === "ico_sphere") return new THREE.IcosahedronGeometry(Math.max(w, d, h) / 2, 2);
  if (type === "cone") return new THREE.ConeGeometry(Math.max(w, d) / 2, h, 32);
  if (type === "torus") return new THREE.TorusGeometry(Math.max(w, d) / 2, Math.max(0.01, h / 2), 16, 48);
  if (type === "plane") return new THREE.PlaneGeometry(w, d);
  return new THREE.BoxGeometry(w, h, d);
}

function createMaterial(object: WorkflowSceneObject, wireframe: boolean, selected: boolean) {
  const isAccent = /accent|strip|core|emissive|glow/i.test(object.name + object.materialName);
  const isMetal = /metal|hoop|bevel|dark/i.test(object.name + object.materialName);
  const isWood = /wood|barrel|table|leg/i.test(object.name + object.materialName);

  return new THREE.MeshStandardMaterial({
    color: selected ? 0x38bdf8 : isAccent ? 0x06b6d4 : isWood ? 0x8b5a2b : isMetal ? 0x1f2937 : 0x334155,
    metalness: selected || isMetal || isAccent ? 0.78 : 0.2,
    roughness: isWood ? 0.65 : selected ? 0.25 : 0.35,
    emissive: selected ? 0x0f172a : isAccent ? 0x06b6d4 : 0x000000,
    emissiveIntensity: selected ? 0.4 : isAccent ? 1.6 : 0,
    wireframe,
  });
}

function addEdges(mesh: THREE.Mesh) {
  const edges = new THREE.EdgesGeometry(mesh.geometry, 25);
  const line = new THREE.LineSegments(
    edges,
    new THREE.LineBasicMaterial({ color: 0x38bdf8, transparent: true, opacity: 0.35 })
  );
  mesh.add(line);
}

export function ThreeViewport({
  assetSpec,
  sceneObjects = [],
  wireframeMode = false,
  selectedObjectName = null,
  onObjectSelect,
}: ThreeViewportProps) {
  const { theme, systemTheme } = useTheme();
  const isDark = theme === "dark" || (theme === "system" && systemTheme === "dark");

  const containerRef = useRef<HTMLDivElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshGroupRef = useRef<THREE.Group | null>(null);
  const autoRotateRef = useRef(false);

  const [wireframe, setWireframe] = useState(false);
  const [autoRotate, setAutoRotate] = useState(false);
  const [cameraView, setCameraView] = useState<"iso" | "front" | "top">("iso");
  const effectiveWireframe = wireframe || wireframeMode;

  useEffect(() => {
    autoRotateRef.current = autoRotate;
  }, [autoRotate]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const scene = new THREE.Scene();
    sceneRef.current = scene;

    const camera = new THREE.PerspectiveCamera(
      45,
      container.clientWidth / container.clientHeight,
      0.1,
      100
    );
    camera.position.set(2.4, 2.0, 3.2);
    cameraRef.current = camera;

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    renderer.setSize(container.clientWidth, container.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.15;
    renderer.setClearColor(0x000000, 0); // Transparent background
    rendererRef.current = renderer;

    container.innerHTML = "";
    container.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(0, 0.4, 0);
    controls.maxPolarAngle = Math.PI / 2 + 0.05;
    controls.minDistance = 0.5;
    controls.maxDistance = 15;
    controlsRef.current = controls;

    const keyLight = new THREE.DirectionalLight(0xffffff, 1.8);
    keyLight.position.set(4, 8, 5);
    keyLight.castShadow = true;
    keyLight.shadow.mapSize.width = 2048;
    keyLight.shadow.mapSize.height = 2048;
    keyLight.shadow.bias = -0.0001;
    scene.add(keyLight);

    const fillLight = new THREE.DirectionalLight(0x06b6d4, 1.0);
    fillLight.position.set(-5, 3, -4);
    scene.add(fillLight);

    const rimLight = new THREE.DirectionalLight(0xa855f7, 1.2);
    rimLight.position.set(0, 5, -6);
    scene.add(rimLight);

    let animationFrameId: number;
    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      controls.update();
      if (autoRotateRef.current && meshGroupRef.current) {
        meshGroupRef.current.rotation.y += 0.004;
      }
      renderer.render(scene, camera);
    };
    animate();

    const resizeObserver = new ResizeObserver(() => {
      const w = container.clientWidth;
      const h = container.clientHeight;
      if (w === 0 || h === 0) return;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    });
    resizeObserver.observe(container);

    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      renderer.dispose();
      scene.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          if (Array.isArray(object.material)) {
            object.material.forEach((material) => material.dispose());
          } else {
            object.material.dispose();
          }
        }
      });
    };
  }, [onObjectSelect]);

  useEffect(() => {
    const scene = sceneRef.current;
    if (!scene) return;

    const oldHemi = scene.getObjectByName("hemiLight");
    if (oldHemi) scene.remove(oldHemi);
    const oldGrid = scene.getObjectByName("gridHelper");
    if (oldGrid) scene.remove(oldGrid);
    const oldFloor = scene.getObjectByName("floor");
    if (oldFloor) scene.remove(oldFloor);

    const hemiLight = new THREE.HemisphereLight(0xffffff, isDark ? 0x444455 : 0x8d8d91, 0.6);
    hemiLight.position.set(0, 10, 0);
    hemiLight.name = "hemiLight";
    scene.add(hemiLight);

    const gridHelper = new THREE.GridHelper(100, 100, 0x0ea5e9, isDark ? 0x334155 : 0xe2e8f0);
    gridHelper.name = "gridHelper";
    gridHelper.material.transparent = true;
    gridHelper.material.onBeforeCompile = (shader) => {
      shader.vertexShader = `
        varying vec3 vWorldPosition;
        ${shader.vertexShader}
      `.replace(
        `#include <worldpos_vertex>`,
        `#include <worldpos_vertex>\n vWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;`
      );
      shader.fragmentShader = `
        varying vec3 vWorldPosition;
        ${shader.fragmentShader}
      `.replace(
        `vec4 diffuseColor = vec4( diffuse, opacity );`,
        `
        float dist = length(vWorldPosition.xz);
        float fade = 1.0 - smoothstep(4.0, 12.0, dist);
        vec4 diffuseColor = vec4( diffuse, opacity * fade );
        `
      );
    };
    scene.add(gridHelper);

    const floor = new THREE.Mesh(
      new THREE.PlaneGeometry(100, 100),
      new THREE.ShadowMaterial({ opacity: isDark ? 0.4 : 0.18, transparent: true })
    );
    floor.name = "floor";
    floor.rotation.x = -Math.PI / 2;
    floor.receiveShadow = true;
    (floor.material as THREE.ShadowMaterial).onBeforeCompile = (shader) => {
      shader.vertexShader = `
        varying vec3 vWorldPosition;
        ${shader.vertexShader}
      `.replace(
        `#include <worldpos_vertex>`,
        `#include <worldpos_vertex>\n vWorldPosition = (modelMatrix * vec4(position, 1.0)).xyz;`
      );
      shader.fragmentShader = `
        varying vec3 vWorldPosition;
        ${shader.fragmentShader}
      `.replace(
        `gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) );`,
        `
        float dist = length(vWorldPosition.xz);
        float fade = 1.0 - smoothstep(2.0, 10.0, dist);
        gl_FragColor = vec4( color, opacity * ( 1.0 - getShadowMask() ) * fade );
        `
      );
    };
    scene.add(floor);
  }, [isDark]);

  useEffect(() => {
    const scene = sceneRef.current;
    const renderer = rendererRef.current;
    const camera = cameraRef.current;
    if (!scene) return;

    if (meshGroupRef.current) {
      scene.remove(meshGroupRef.current);
      meshGroupRef.current.traverse((object) => {
        if (object instanceof THREE.Mesh) {
          object.geometry.dispose();
          if (Array.isArray(object.material)) {
            object.material.forEach((material) => material.dispose());
          } else {
            object.material.dispose();
          }
        }
      });
    }

    const group = new THREE.Group();
    sceneObjects.forEach((object) => {
      const selected = object.name === selectedObjectName;
      const mesh = new THREE.Mesh(
        createGeometry(object),
        createMaterial(object, effectiveWireframe, selected)
      );
      const [x, y, z] = object.location;
      mesh.position.set(x, z, y);
      if (object.rotation) {
        const [rx, ry, rz] = object.rotation;
        mesh.rotation.set(rx, rz, ry);
      }
      if (object.primitiveType === "torus") {
        mesh.rotation.x = Math.PI / 2;
      }
      mesh.name = object.name;
      mesh.userData = { objectName: object.name };
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      addEdges(mesh);
      if (selected) {
        mesh.scale.setScalar(1.02);
      }
      group.add(mesh);
    });

    scene.add(group);
    meshGroupRef.current = group;

    if (renderer && camera) {
      const raycaster = new THREE.Raycaster();
      const pointer = new THREE.Vector2();
      const handlePointerDown = (event: PointerEvent) => {
        const rect = renderer.domElement.getBoundingClientRect();
        if (rect.width === 0 || rect.height === 0) return;

        pointer.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
        pointer.y = -(((event.clientY - rect.top) / rect.height) * 2 - 1);
        raycaster.setFromCamera(pointer, camera);

        const intersections = raycaster.intersectObjects(group.children, true);
        const hit = intersections.find((intersection) => intersection.object instanceof THREE.Mesh)?.object;
        onObjectSelect?.(hit?.name || null);
      };

      renderer.domElement.addEventListener("pointerdown", handlePointerDown);
      return () => {
        renderer.domElement.removeEventListener("pointerdown", handlePointerDown);
      };
    }
  }, [sceneObjects, effectiveWireframe, selectedObjectName, onObjectSelect]);

  const handleSetView = (view: "iso" | "front" | "top") => {
    setCameraView(view);
    if (!cameraRef.current || !controlsRef.current) return;

    if (view === "iso") {
      cameraRef.current.position.set(2.4, 2.0, 3.2);
      controlsRef.current.target.set(0, 0.4, 0);
    } else if (view === "front") {
      cameraRef.current.position.set(0, 0.6, 4.0);
      controlsRef.current.target.set(0, 0.5, 0);
    } else {
      cameraRef.current.position.set(0, 4.5, 0.01);
      controlsRef.current.target.set(0, 0, 0);
    }
    controlsRef.current.update();
  };

  return (
    <div className="relative w-full h-full min-h-120 rounded-2xl overflow-hidden border border-border bg-card flex flex-col">
      <div className="absolute top-4 left-4 right-4 z-10 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-2 pointer-events-auto">
          <Badge variant="outline" className="bg-background/85 backdrop-blur-md border-cyan-500/40 text-cyan-300 text-xs px-2.5 py-1 font-semibold">
            <Box className="w-3.5 h-3.5 mr-1 text-cyan-400" />
            {assetSpec?.asset_type ? assetSpec.asset_type.toUpperCase() : "READY"}
          </Badge>
          <Badge variant="outline" className="bg-background/75 backdrop-blur-md text-xs text-muted-foreground font-mono">
            {sceneObjects.length} live objects
          </Badge>
        </div>

        <div className="flex items-center gap-1 pointer-events-auto bg-background/85 backdrop-blur-md p-1 rounded-xl border border-border shadow-lg">
          <div className="flex bg-muted/40 p-0.5 rounded-lg mr-1">
            <Button
              size="sm"
              variant="ghost"
              onClick={() => handleSetView("iso")}
              className={`h-7 px-2 text-xs ${cameraView === "iso" ? "text-primary bg-primary/10" : "text-muted-foreground"}`}
            >
              Iso
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => handleSetView("front")}
              className={`h-7 px-2 text-xs ${cameraView === "front" ? "text-primary bg-primary/10" : "text-muted-foreground"}`}
            >
              Front
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => handleSetView("top")}
              className={`h-7 px-2 text-xs ${cameraView === "top" ? "text-primary bg-primary/10" : "text-muted-foreground"}`}
            >
              Top
            </Button>
          </div>

          <Button
            size="sm"
            variant="ghost"
            className={`h-7 px-2 text-xs ${effectiveWireframe ? "text-cyan-400 bg-cyan-500/10" : "text-muted-foreground"}`}
            onClick={() => setWireframe((prev) => !prev)}
            title="Toggle Wireframe Overlay"
          >
            <BoneFracture className="w-3.5 h-3.5 mr-1" />
          </Button>

          <Button
            size="sm"
            variant="ghost"
            className={`h-7 px-2 text-xs ${autoRotate ? "text-primary bg-primary/10" : "text-muted-foreground"}`}
            onClick={() => setAutoRotate((prev) => !prev)}
            title="Toggle Turntable Rotation"
          >
            <Rotate3d className="w-3.5 h-3.5 mr-1" />
          </Button>
        </div>
      </div>

      {sceneObjects.length === 0 && (
        <div className="absolute inset-x-0 top-20 z-10 flex justify-center pointer-events-none">
          <Badge variant="outline" className="bg-background/85 text-muted-foreground">
            Waiting for agent-created geometry
          </Badge>
        </div>
      )}

      <div ref={containerRef} className="w-full flex-1 min-h-110 cursor-grab active:cursor-grabbing" />
    </div>
  );
}
