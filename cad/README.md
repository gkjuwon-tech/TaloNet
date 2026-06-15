# `cad/` — TaloNet 기체 CAD / SCAD 설계

그물매(Geulmae) 모선드론의 **파라메트릭 형상 모델**. 양산용 응력해석 모델이 아니라
**매싱(massing) + 마운팅 지오메트리 + 패키징 검증용** 설계다. 모든 치수는
[`docs/01_드론_스펙.md`](../docs/01_드론_스펙.md)에서 추적된다.

## 파일
| 파일 | 설명 |
|------|------|
| `talonet_frame.scad` | X8 동축 옥토콥터 기체 전체 파라메트릭 모델 |
| `forensic_appliance.scad` | **ForensIQ-1 사후 포렌식 기기** 파라메트릭 인클로저 (카드 삽입 → 분석 → 내장 프린터) |

---

## `forensic_appliance.scad` — ForensIQ-1 포렌식 기기

포획한 적 드론의 microSD/SD를 **write-block 슬롯**에 꽂으면 `forensics/` 파이프라인이
이미징→해시→파싱→항적/의도 분석 후 **내장 80mm 열전사 프린터**로 위협 인텔 리포트를
출력하고 PDF를 증거 USB에 보관하는 **밀폐 키오스크**. 설계: [`docs/09`](../docs/09_Forensic_Appliance_Design.md),
운용: [`docs/10`](../docs/10_Forensic_Appliance_Operator_Guide.md).

> **설계 포인트(매니폴드):** 구멍이 필요한 앞면 피처(스크린 창·카드 슬롯·용지 배출구)는
> **창이 내장된 자기완결형 솔리드**로 만들어 **몸체를 자른 뒤 union**으로 얹는다. 그래서
> 패널 컷이 피처를 절대 먹지 않고 2-매니폴드를 유지한다.
> 검증: `Simple: yes` (≈3,566 verts / 2,398 facets, OpenSCAD 2021.01).

### 렌더
```bash
openscad -o appliance.stl cad/forensic_appliance.scad
# 3/4 히어로 프리뷰 (헤드리스: xvfb-run)
xvfb-run -a openscad -o hero.png --imgsize=1300,950 \
    --camera=0,0,93,60,0,-120,1180 cad/forensic_appliance.scad
```

### 주요 파라미터 (Customizer)
| 그룹 | 파라미터 | 기본값 | 의미 |
|------|----------|--------|------|
| Case body | `case_w/d/h` | 420/320/220 | 외형 폭/깊이/높이 mm |
| | `wall_thk` / `edge_cham` | 6 / 10 | 벽 두께 / 러기드 모서리 챔퍼 |
| | `lid_h` | 34 | 상단 클램셸 리드 밴드 |
| Handle | `handle_d` / `handle_rise` | 22 / 46 | 캐리 핸들 바 직경 / 높이 |
| Touchscreen | `screen_diag_in` / `screen_16_10` | 7 / true | 화면 대각(in) / 16:10 |
| | `screen_bezel` | 10 | 베젤 폭 |
| Write-blocker | `wb_block_w/h` | 96/66 | 라이트블로커 모듈 블록 |
| | `usd_slot_w/h`, `sd_slot_w/h` | 16/3, 26/3.4 | microSD / SD 슬롯 |
| Printer | `printer_bay_w/h`, `paper_slot_w/h`, `roll_od` | 118/96, 86/5, 70 | 프린터 베이 / 용지 배출 / 롤 |
| Controls | `btn_dia`, `led_dia`, `led_count`, `keylock_dia` | 16, 7, 5, 20 | 버튼/LED/키락 |
| Internals | `show_internals`, `lid_open`, `sbc_board_w/d`, `fan_dia` | true, 0, 100/80, 60 | 내부 매싱/익스플로드/SBC/팬 |
| Rear | `vent_louvres` | 6 | 후면 통풍 루버 |

### 모듈
- `body()` / `lid()` / `carry_handle()` — 러기드 인클로저 + 리드 + 핸들
- `bezel_window()` / `face_stud()` — **창 내장 베젤 프레임** / 양각 버튼·LED·키락 헬퍼
- `front_features()` — 터치스크린 + 라이트블로커(슬롯+녹색 BLOCKED LED) + 프린터 배출구 + 컨트롤
- `front_wall_cuts()` / `rear_ports()` / `rear_cuts()` — 앞면 창 관통 / 후면 포트·통풍
- `internals()` — SBC + 라이트블로커 PCB + 80mm 프린터+용지롤 + 팬 + UPS

## 렌더 / 익스포트

```bash
# STL 익스포트 (제조/슬라이서/외부 CAD 반입용)
openscad -o talonet_frame.stl talonet_frame.scad

# PNG 프리뷰 (헤드리스 서버는 xvfb-run 사용)
xvfb-run -a openscad -o preview.png --imgsize=1500,1050 \
    --camera=40,0,-150,58,0,32,3600 talonet_frame.scad
```

검증 결과: `Simple: yes` (manifold), vertices ≈ 19,999 / facets ≈ 13,517 (시닝 + 소프트웨어 조준 짐벌 포함).
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
| Capture net | `net_radius/depth` | 430/560 | 펼쳐지는 포획망 마우스 반경/깊이 |
| | `net_rings/spokes` | 6/16 | 메시 후프/스포크 수 |
| | `net_drop_off` | 30 | 그물 정점의 벨리 아래 오프셋 |
| | `net_launched` | true | **발사형**(쏴서 날아가 펼쳐짐) on/off |
| | `net_launch_dist/spread` | 170/1.18 | 발사 사출 거리 / 마우스 확산 배율 |
| Cinch | `cinch_spool_dia/w` | 38/26 | 입구 조임 드로스트링 스풀(플랜지경/드럼폭) |
| | `cinch_motor_dia/len` | 28/56 | 브러시 기어모터 캔(직경/길이) |
| | `cinch_pos_x/drop` | 120/24 | 스풀 어셈블리 위치(X) / 벨리 아래 드롭 |
| | `cinch_guide_d` | 9 | 드로스트링 가이드 아이렛 보어 |
| Net aim | `net_pan/tilt` | 0/16 | **소프트웨어 조준**: 그물 발사 팬(좌우)/틸트(앞뒤) deg |
| | `aim_servo` | 24 | 팬/틸트 조준 서보 블록 크기 |
| | `gimbal_ring_d` | 92 | 팬 베어링 / 틸트 요크 링 직경 |
| Battery | `batt_w/l/h` | 170/210/75 | 배터리 팩 |

> 파라미터만 바꾸면 6S/12S 변형, 더 큰 휠베이스, 비(非)동축 헥사 등으로 즉시 재구성된다.

## 모델 구성 (모듈)

- `deck_plate()` — 육각 카본 데크(상/하), 경량화 홀 + 케이블 관통구
- `arm()` / `motor_mount()` / `motor()` — 암 클램프 + 카본 튜브 + 동축 모터 마운트
- `avionics_stack()` — FC + 컴패니언(Jetson Orin 매싱) + PDB 패키징
- `netlauncher_bay()` — 벨리 넷런처 베이(머즐 개구부 포함)
- `winch_release()` — 윈치 드럼 + 전자식 퀵릴리스 액추에이터 (상하 권취 = **별도 장치**)
- `cinch_mechanism()` — **그물 입구 조임 전용 구동장치**: 브러시 기어모터 + 플랜지 스풀(드럼) + 장력/엔코더 픽업 + 드로스트링 가이드 아이렛. 림 둘레 퍼스라인(드로스트링)을 감아 mouth를 졸라 닫는다. 윈치(상하 권취)와 **물리적으로 분리된** 액추에이터
- `net_launcher()` — **소프트웨어 조준 스마트 그물 런처**: 팬/틸트 짐벌(서보 2개) + 요크 + 머즐 노즐. `net_pan`/`net_tilt`로 머즐을 틀어 **그물을 조준해서 발사**(중력 낙하 X). 그물·시닝 전체가 조준 방향으로 함께 스윙. 지상조종(GCS)에서 제어
- `capture_net()` — **발사형 포획망**: 머즐에서 쏴서 `net_launch_dist`만큼 사출되어 펼쳐지는 캐스팅 네트(선단 림 추가 넓게 확산 + 메시 + 머즐로 되돌아가는 트레일링 발사 라인). 포획 드론은 이 포켓에 담아 운반
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
