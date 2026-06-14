# `cad/` — TaloNet 기체 CAD / SCAD 설계

그물매(Geulmae) 모선드론의 **파라메트릭 형상 모델**. 양산용 응력해석 모델이 아니라
**매싱(massing) + 마운팅 지오메트리 + 패키징 검증용** 설계다. 모든 치수는
[`docs/01_드론_스펙.md`](../docs/01_드론_스펙.md)에서 추적된다.

## 파일
| 파일 | 설명 |
|------|------|
| `talonet_frame.scad` | X8 동축 옥토콥터 기체 전체 파라메트릭 모델 |

## 렌더 / 익스포트

```bash
# STL 익스포트 (제조/슬라이서/외부 CAD 반입용)
openscad -o talonet_frame.stl talonet_frame.scad

# PNG 프리뷰 (헤드리스 서버는 xvfb-run 사용)
xvfb-run -a openscad -o preview.png --imgsize=1500,1050 \
    --camera=40,0,-150,58,0,32,3600 talonet_frame.scad
```

검증 결과: `Simple: yes` (manifold), vertices ≈ 8,122 / facets ≈ 4,362, 렌더 ~8.5 s.
OpenSCAD 2021.01에서 STL 익스포트·매니폴드 통과 확인됨.

## 주요 파라미터 (Customizer)

| 그룹 | 파라미터 | 기본값 | 의미 |
|------|----------|--------|------|
| Airframe | `wheelbase` | 1150 | 모터-모터 대각(휠베이스) mm |
| | `arm_count` | 4 | 암 개수 (X8 = 4암 × 2모터) |
| | `coaxial` | true | 동축(상하 2모터) 여부 |
| | `arm_yaw_offset` | 45 | 암 십자 회전(45 = X배열) |
| Arms | `arm_tube_od/id` | 30/26 | 카본 튜브 외/내경 |
| Props | `prop_dia` | 711 | ~28in 폴딩 프롭 직경 |
| Landing gear | `gear_height/track` | 230/520 | 랜딩기어 높이/트랙 |
| Net bay | `bay_w/l/h` | 240/300/130 | 벨리 넷런처 베이 |
| Capture net | `net_radius/depth` | 430/560 | 아래로 벌어지는 포획망(깔때기 포켓) |
| | `net_rings/spokes` | 6/16 | 메시 후프/스포크 수 |
| | `net_drop_off` | 30 | 그물 정점의 벨리 아래 오프셋 |
| Battery | `batt_w/l/h` | 170/210/75 | 배터리 팩 |

> 파라미터만 바꾸면 6S/12S 변형, 더 큰 휠베이스, 비(非)동축 헥사 등으로 즉시 재구성된다.

## 모델 구성 (모듈)

- `deck_plate()` — 육각 카본 데크(상/하), 경량화 홀 + 케이블 관통구
- `arm()` / `motor_mount()` / `motor()` — 암 클램프 + 카본 튜브 + 동축 모터 마운트
- `avionics_stack()` — FC + 컴패니언(Jetson Orin 매싱) + PDB 패키징
- `netlauncher_bay()` — 벨리 넷런처 베이(머즐 개구부 포함)
- `winch_release()` — 윈치 드럼 + 전자식 퀵릴리스 액추에이터
- `capture_net()` — **아래로 벌어지는** 포획망(깔때기 캐노피 + 포켓 + 림 추 + 테더). 포획 드론은 이 포켓에 담아 운반
- `landing_gear()` — 아치 스키드 2조
- `battery()` — 상단 데크 배터리 팩

## 시그니처 컬러
기체 강조 컬러는 TaloNet 시그니처 **국방카키 `#86855F`** (`C_KHAKI`)로 통일.

## 외부 CAD 연계 (Fusion/SolidWorks/FreeCAD)
- `talonet_frame.scad` → STL/3MF 익스포트 후 외부 MCAD로 반입해 상세설계(볼트홀, 체결,
  케이블 라우팅, 응력해석)를 진행한다.
- 형상의 **단일 진실원천(single source of truth)** 은 이 SCAD의 파라미터 세트로 둔다.
- 회로/배선은 [`docs/06_회로_설계.md`](../docs/06_회로_설계.md), 하드웨어 연동 SW는
  [`docs/07_소프트웨어_기획.md`](../docs/07_소프트웨어_기획.md) 참조.
