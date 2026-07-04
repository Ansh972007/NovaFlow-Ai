"use client";

import { useRef, useState, useEffect, useMemo, useCallback, Suspense } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { useGLTF, useAnimations, ContactShadows, Environment } from "@react-three/drei";
import * as THREE from "three";
import { clone as cloneSkinned } from "three/addons/utils/SkeletonUtils.js";

const MODEL_PATH = "/models/xbot.glb";
const MODEL_SCALE = 0.58;
const CAM = { x: 0, y: 1.05, z: 3.6 };
const LOOK_Y = 0.9;
const IDLE_FACE_Y = 0;
const HI_DURATION = 3.2;

function lerpAngle(current, target, t) {
  const diff = ((target - current + Math.PI) % (Math.PI * 2)) - Math.PI;
  return current + diff * Math.min(1, t);
}

function prepareXbotModel(object) {
  object.traverse((child) => {
    if (!child.isMesh) return;
    child.castShadow = true;
    child.receiveShadow = true;
    child.frustumCulled = false;
    if (child.material) {
      const mats = Array.isArray(child.material) ? child.material : [child.material];
      mats.forEach((m) => {
        m.envMapIntensity = 1.2;
      });
    }
  });
}

function fitXbotToGround(object) {
  const box = new THREE.Box3().setFromObject(object);
  object.position.y -= box.min.y;
  object.position.x -= (box.min.x + box.max.x) / 2;
  object.position.z -= (box.min.z + box.max.z) / 2;
}

function pickAction(actions, names, candidates) {
  for (const key of candidates) {
    if (actions[key]) return actions[key];
  }
  const lower = Object.fromEntries(names.map((n) => [n.toLowerCase(), actions[n]]));
  for (const key of candidates) {
    if (lower[key.toLowerCase()]) return lower[key.toLowerCase()];
  }
  return null;
}

function NovaCharacter({ targetX, charPosRef, greeting, patrolEnabled, hiWave, onHiClick }) {
  const root = useRef();
  const pos = useRef(new THREE.Vector3(0, 0, 0));
  const isHi = useRef(false);
  const hiT = useRef(0);
  const animState = useRef("idle");
  const booted = useRef(false);

  const { scene, animations } = useGLTF(MODEL_PATH);
  const model = useMemo(() => {
    const clone = cloneSkinned(scene);
    prepareXbotModel(clone);
    fitXbotToGround(clone);
    return clone;
  }, [scene]);

  const { actions, names, mixer } = useAnimations(animations, root);

  useEffect(() => {
    pos.current.x = 0;
    booted.current = false;
    if (root.current) {
      root.current.rotation.set(0, IDLE_FACE_Y, 0);
      root.current.position.set(0, 0, 0);
    }
    const t = setTimeout(() => { booted.current = true; }, 150);
    return () => clearTimeout(t);
  }, []);

  const fadeTo = useCallback((nextKey, duration = 0.2) => {
    if (!names.length) return;
    const walk = pickAction(actions, names, ["walk", "Walk"]);
    const idle = pickAction(actions, names, ["idle", "Idle"]);
    const agree = pickAction(actions, names, ["agree", "Agree"]);
    const map = { walk, idle, agree };
    const next = map[nextKey] || idle;
    if (!next || animState.current === nextKey) return;
    const current = map[animState.current];

    if (nextKey === "agree") {
      next.reset();
      next.setLoop(THREE.LoopOnce, 1);
      next.clampWhenFinished = true;
      next.setEffectiveTimeScale(1).fadeIn(duration).play();
    } else {
      next.reset().setLoop(THREE.LoopRepeat, Infinity);
      next.clampWhenFinished = false;
      next.setEffectiveTimeScale(nextKey === "walk" ? 1.05 : 1).fadeIn(duration).play();
    }
    if (current && current !== next) current.fadeOut(duration);
    animState.current = nextKey;
  }, [actions, names]);

  const startHi = useCallback(() => {
    isHi.current = true;
    hiT.current = 0;
    pos.current.set(0, 0, 0);
    if (root.current) {
      root.current.position.set(0, 0, 0);
      root.current.rotation.set(0, IDLE_FACE_Y, 0);
    }
    fadeTo("agree", 0.12);
  }, [fadeTo]);

  useEffect(() => {
    const idle = pickAction(actions, names, ["idle", "Idle"]);
    idle?.reset().fadeIn(0.25).play();
    animState.current = "idle";
  }, [actions, names]);

  useEffect(() => {
    if (!mixer) return;
    const onDone = (e) => {
      const clip = e.action?.getClip?.();
      if (clip?.name?.toLowerCase() === "agree" && isHi.current) {
        fadeTo("idle", 0.25);
      }
    };
    mixer.addEventListener("finished", onDone);
    return () => mixer.removeEventListener("finished", onDone);
  }, [mixer, fadeTo]);

  useEffect(() => {
    if (!hiWave) return;
    startHi();
  }, [hiWave, startHi]);

  useFrame((_, delta) => {
    if (!root.current) return;

    if (isHi.current) {
      hiT.current += delta;
      root.current.rotation.x = 0;
      root.current.rotation.y = lerpAngle(root.current.rotation.y, IDLE_FACE_Y, delta * 8);
      root.current.position.set(0, 0, 0);
      charPosRef.current.set(0, 0, 0);
      if (hiT.current > HI_DURATION) {
        isHi.current = false;
        fadeTo("idle", 0.25);
      }
      return;
    }

    if (!patrolEnabled) {
      root.current.rotation.y = IDLE_FACE_Y;
      root.current.position.set(0, 0, 0);
      charPosRef.current.set(0, 0, 0);
      fadeTo("idle", 0.2);
      return;
    }

    const dx = targetX - pos.current.x;
    const moving = Math.abs(dx) > 0.02;

    if (moving) {
      pos.current.x += Math.sign(dx) * Math.min(Math.abs(dx), delta * 1.35);
    }

    root.current.position.set(pos.current.x, 0, 0);
    charPosRef.current.copy(pos.current);

    if (moving) {
      const targetY = dx > 0 ? -Math.PI / 2 : Math.PI / 2;
      root.current.rotation.y = booted.current
        ? lerpAngle(root.current.rotation.y, targetY, delta * 7)
        : targetY;
      fadeTo("walk", 0.15);
    } else {
      root.current.rotation.y = booted.current
        ? lerpAngle(root.current.rotation.y, IDLE_FACE_Y, delta * 5)
        : IDLE_FACE_Y;
      fadeTo("idle", 0.2);
    }
  });

  const handleClick = useCallback((e) => {
    e.stopPropagation();
    onHiClick?.();
  }, [onHiClick]);

  return (
    <group ref={root} scale={MODEL_SCALE}>
      <primitive object={model} onClick={handleClick} />
      <mesh position={[0, 0.95, 0]} onClick={handleClick}>
        <capsuleGeometry args={[0.32, 0.85, 6, 12]} />
        <meshBasicMaterial visible={false} />
      </mesh>
    </group>
  );
}

function CameraRig({ charPosRef }) {
  const { camera } = useThree();
  const look = useRef(new THREE.Vector3());
  useFrame((_, delta) => {
    const x = charPosRef.current.x * 0.45;
    look.current.set(x, LOOK_Y, 0);
    camera.position.lerp(new THREE.Vector3(x, CAM.y, CAM.z), Math.min(1, delta * 3));
    camera.lookAt(look.current);
  });
  return null;
}

function SceneContent({ greeting }) {
  const { size } = useThree();
  const [targetX, setTargetX] = useState(0);
  const [patrolEnabled, setPatrolEnabled] = useState(false);
  const [hiWave, setHiWave] = useState(0);
  const charPosRef = useRef(new THREE.Vector3(0, 0, 0));
  const patrolDir = useRef(-1);
  const xBound = useRef(0.5);
  const greetLock = useRef(false);

  const clampX = useCallback((x) => THREE.MathUtils.clamp(x, -xBound.current, xBound.current), []);

  const triggerHi = useCallback(() => {
    if (greetLock.current) return;
    greetLock.current = true;
    setTargetX(0);
    setHiWave((n) => n + 1);
    setTimeout(() => { greetLock.current = false; }, HI_DURATION * 1000 + 200);
  }, []);

  useEffect(() => {
    xBound.current = 0.5 * Math.min(1, size.width / Math.max(size.height, 1));
  }, [size]);

  useEffect(() => {
    const enable = setTimeout(() => setPatrolEnabled(true), 1800);
    return () => clearTimeout(enable);
  }, []);

  useEffect(() => {
    if (!greeting) return;
    greetLock.current = true;
    setTargetX(0);
    setHiWave((n) => n + 1);
    const t = setTimeout(() => { greetLock.current = false; }, HI_DURATION * 1000 + 200);
    return () => clearTimeout(t);
  }, [greeting]);

  useEffect(() => {
    if (!patrolEnabled) return;
    const patrol = () => {
      if (greetLock.current) return;
      setTargetX((prev) => {
        const bound = xBound.current * 0.78;
        if (prev >= bound * 0.85) patrolDir.current = -1;
        if (prev <= -bound * 0.85) patrolDir.current = 1;
        return patrolDir.current > 0 ? bound : -bound;
      });
    };
    const t = setTimeout(patrol, 500);
    const loop = setInterval(patrol, 4800);
    return () => { clearTimeout(t); clearInterval(loop); };
  }, [greeting, patrolEnabled]);

  return (
    <>
      <ambientLight intensity={0.7} color="#e4e4e7" />
      <directionalLight position={[4, 7, 5]} intensity={2.2} color="#ffffff" castShadow />
      <directionalLight position={[-5, 3, -4]} intensity={1.3} color="#a78bfa" />
      <directionalLight position={[0, 2, -6]} intensity={0.85} color="#fafafa" />
      <spotLight position={[2, 4, 3]} angle={0.45} penumbra={0.7} intensity={2.2} color="#f5f3ff" distance={14} />
      <pointLight position={[0, 1.4, 1.5]} intensity={1.1} color="#c4b5fd" distance={7} />
      <Environment preset="city" />

      <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, 0, 0]} receiveShadow>
        <circleGeometry args={[2, 64]} />
        <meshStandardMaterial color="#0a0a0a" metalness={0.85} roughness={0.35} transparent opacity={0.2} />
      </mesh>

      <mesh
        rotation={[-Math.PI / 2, 0, 0]}
        onClick={(e) => { e.stopPropagation(); if (!greetLock.current) setTargetX(clampX(e.point.x)); }}
      >
        <planeGeometry args={[10, 10]} />
        <meshBasicMaterial visible={false} />
      </mesh>

      <ContactShadows position={[0, 0, 0]} opacity={0.6} scale={4.5} blur={2.5} far={2.5} color="#000000" />
      <CameraRig charPosRef={charPosRef} />
      <NovaCharacter
        targetX={targetX}
        charPosRef={charPosRef}
        greeting={greeting}
        patrolEnabled={patrolEnabled}
        hiWave={hiWave}
        onHiClick={triggerHi}
      />
    </>
  );
}

export default function Nova3DScene({ greeting = 0 }) {
  return (
    <Canvas
      id="nova-3d-canvas"
      className="!absolute inset-0 h-full w-full"
      style={{ pointerEvents: "auto", cursor: "pointer" }}
      camera={{ position: [CAM.x, CAM.y, CAM.z], fov: 36, near: 0.1, far: 100 }}
      gl={{ antialias: true, alpha: true }}
      shadows
      dpr={[1, 2]}
      onCreated={({ gl }) => {
        gl.setClearColor(0x000000, 0);
        gl.toneMapping = THREE.ACESFilmicToneMapping;
        gl.toneMappingExposure = 1.4;
      }}
    >
      <Suspense fallback={null}>
        <SceneContent greeting={greeting} />
      </Suspense>
    </Canvas>
  );
}

useGLTF.preload(MODEL_PATH);
