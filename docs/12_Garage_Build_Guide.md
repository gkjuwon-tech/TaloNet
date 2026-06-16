# 12. 차고 수제작 가이드 (따라하면 진짜 만들어짐)

> **부제: 방산기업이 없어서 차고에서 시작한다 (feat. 옆집 김씨의 항의)**
>
> [BOM(.xlsx)](../bom/TaloNet_BOM.xlsx) / [BOM(.pdf)](../bom/TaloNet_BOM.pdf)대로 부품 사서,
> **CNC는 외주 발품 + 나머지는 차고에서** 두 완성품 — **그물 드론(Peregrine)** + **포렌식
> 기기(ForensIQ-1)** — 을 만들어 **소프트웨어(`gcs/`/`forensics/`)랑 실제로 통신되고 스펙
> 목표치 다 돌아가게** 만드는 **단계별 매뉴얼**이다. 추상적인 "조립하세요" 아님 — **나사 규격,
> 와이어 굵기, ArduPilot 파라미터 값, 확인 명령어와 기대 출력까지** 다 적었다. 길다. 따라와라.
>
> 각 페이즈 끝의 **`✅ CHECKPOINT`** 를 통과 못 하면 다음으로 넘어가지 마라. 안 그러면
> 나중에 50V가 당신 손가락을 통해 흐른다.

**전체 페이즈 맵:** P0 수령검수 → P1 안전셋업 → P2 발주/외주 → P3 프레임 → P4 추진 →
P5 항전/전원 → P6 그물 페이로드 → P7 하네스 → P8 펌웨어 → P9 포렌식기기 →
P10 SW 브링업 → P11 서보 캘리브 → P12 벤치테스트 → P13 비행시험 → P14 트러블슈팅 → P15 DONE.

예상 소요: **풀타임 3~5주**(외주 리드타임 별도). 혼자 하면 6주 + 이혼.

---

## P0. 수령 검수 (Receiving) — 30분

부품 도착하면 BOM 열고 **ID별로 체크**. 특히:
- **모터 8개** 동일 로트/방향성, **ESC 8개**, **프롭 CW 4 / CCW 4** 페어 맞는지.
- **배터리**: 외형 부풀음/찍힘 없는지(있으면 **즉시 반품**, 차고에 들이지 마라).
- **mosaic-X5 / Jetson** 같은 비싼 애들은 ESD 백째 보관, 정전기 매트 위에서만 개봉.
- 누락분은 지금 재주문(P6에서 부품 하나 없어서 일주일 멈추는 게 국룰).

> `✅ CHECKPOINT P0`: BOM 70개 라인 전부 ✔ 또는 "발주됨". 손상품 0.

---

## P1. 차고 셋업 & 안전 — 반나절 (생략하면 진짜 죽음)

### 1.1 작업대 3구역
- **전자존**: ESD 매트 + 접지밴드 + 인두(Hakko) + 흄 익스트랙터.
- **기계존**: 바이스, 토크 드라이버, 3D프린터.
- **위험존(분리·환기)**: LiPo 충전(LiPo-safe 백/금속함), CO2 카트리지 보관.

### 1.2 안전 절대수칙 (BOM `TL-007` 안전킷)
| 위험 | 규칙 |
|------|------|
| 🔋 12S 배터리(50.4V max) | 충전은 **LiPo-safe 백 안에서, 자리 비우지 말 것**. 단자 절대 단락. D급 소화기/모래 비치. 부풀면 폐기. |
| 💨 CO2 솔레노이드/16g 카트리지 | 고압. **정면 금지**. 발사 테스트는 **실외, 사람·창문·강아지 없는 방향**. 첫 테스트는 **그물 빼고 dry-fire**. |
| ✂️ 28" 프롭 ×8 | **손가락 절단기**. 모터 통전 테스트는 **프롭 OFF**. 비행 전까지 프롭은 케이블타이로 결박. |
| 🔥 납땜 | 흄 익스트랙터 + 환기. 무연납이라도 연기 흡입 금지. |
| 👥 2인 원칙 | 통전·발사·비행은 **2명**(1명 작업 + 1명 E-Stop/응급). |

> ⚠️ **법/윤리**: 인가된 운용자용 대드론 체계. 시스템은 **조종·조준·정보 + 사람이 당기는
> 방아쇠**까지(자율무기 아님). 공역/RF/무기류는 **당신 관할 법** 따라라. 비행·발사 전 반드시
> 합법 공역·허가 확인. 변호사 친구 1명 확보.

> `✅ CHECKPOINT P1`: LiPo-safe 충전환경, 소화기, 흄 익스트랙터, E-Stop 더미 준비 완료.

---

## P2. 발주 & 외주 — 리드타임 게임 (Day 1에 쏴라)

### 2.1 발주 순서 (리드타임 역순)
1. **🟨 외주(2~4주, 제일 먼저)**: 카본 데크/암마운트(CNC), **페이로드 IF PCB fab+assembly**. → 2.2.
2. **🟦 롱리드 전자(1~3주)**: mosaic-X5, Jetson AGX Orin, 모터×8 — **품절 잦음, 지금**.
3. **🟦 본체 전자(수일~2주)**: Cube Orange+, ESC×8, RFD900x, Mauch 전원, 배터리, EO/IR 카메라.
4. **🟦 페이로드 소물**: Savox ×3, Pololu G2 ×2, INA226, HX711, CO2 솔레노이드, IRLB3034.
5. **🟩 차고 소모품**: PETG-CF 필라멘트, 실리콘 와이어 키트, 커넥터, M2.5/M3 나사, Loctite 243, 에폭시, 열전사 용지.

### 2.2 외주 — 정확히 뭘 어떻게 보내나
**(a) 카본/알루 (PG-DECK / PG-MNT / PG-GEAR)**
```bash
# SCAD에서 메시 익스포트 (외주샵 견적용)
openscad -o /tmp/peregrine_frame.stl cad/talonet_frame.scad
openscad -o /tmp/peregrine_frame.3mf cad/talonet_frame.scad   # 슬라이서/일부 CNC가 선호
```
- 데크: **3T 카본(CFRP) 또는 G10**, 외형 + 라이트닝홀 + M3 마운트홀. SendCutSend/동네 CNC.
- 모터마운트/클램프: **6061-T6 알루**, 카키 아노다이즈(`OS-AN-001`).
- STEP가 필요하면: STL → FreeCAD 임포트 → Part 변환 → STEP 익스포트.

**(b) 페이로드 IF PCB (PG-PAYIF, STM32G474)** → JLCPCB/PCBWay
- 보낼 것: **거버(Gerber) + BOM + CPL(Pick&Place)**. docs/06 §10 핀맵 기준.
- 옵션: **fab + SMT assembly 같이** 주문(STM32G474 직접 납땜은 지옥). **rev A 5장** 뽑아 여유.
- (KiCad 소스는 아직 미작성 — 이 단계 전에 회로도 캡처 필요. 임시로는 브레드보드/모듈로 인터록 구성 가능: 아밍 릴레이 + MOSFET + INA226 + HX711 모듈을 FC AUX에 직결.)

> `✅ CHECKPOINT P2`: 외주 3건 발주 확인메일 받음, 롱리드 전자 결제 완료.

---

## P3. 드론 프레임 조립 — 반나절

부품: PG-DECK ×2, PG-MNT ×4, 카본암 ×4, PG-GEAR ×2, 스탠드오프킷, M3 나사.

1. **하부 데크**를 ESD 매트에 놓고 중앙 케이블 관통구 확인.
2. **암 클램프(PG-MNT)** 에 카본암(30×26) 삽입 → **2K 에폭시 도포 후 M3×12 볼트 2개**로 클램핑.
   에폭시 경화 24h 동안 다음 암 진행.
3. 4개 암을 하부 데크에 **45° X배열**(arm_yaw_offset=45)로 배치, **M3×8 + 너트**로 고정.
4. **알루 스탠드오프(deck_gap 70mm)** 8개를 데크 사이 기둥으로 → **상부 데크** 덮고 M3×8.
5. **랜딩기어(PG-GEAR)** 아치 2조를 하부 데크 외곽에 M3×10.
6. **모든 나사 = Loctite 243** 한 방울. 토크 **M3 ≈ 0.6 Nm, M4 ≈ 1.5 Nm**(토크드라이버, "느낌" 금지).

> `✅ CHECKPOINT P3`: 프레임 비틀림 없음(평면에서 4암 흔들림 0), 에폭시 완전경화, 전 나사 Loctite.

---

## P4. 추진계 — 모터/ESC/프롭 + 추력검증 (하루)

### 4.1 모터/ESC 장착
1. 각 PG-MNT 끝에 **모터 2개 동축**(상=정방향, 하=역방향) **M4×10**로.
2. **ESC 8개**를 암 안쪽 또는 데크 하부에 케이블타이 + VHB. 방열 고려(가리지 마라).
3. 모터3선 ↔ ESC: **방향은 나중에 펌웨어에서 반전**하므로 우선 임의 결선(테스트 후 확정).
4. ESC 전원입력 ↔ PDB: **6mm 불릿 또는 직납**. 신호선(DShot) ↔ FC 모터레일(M1~M8).

### 4.2 프롭 방향표 (OctoX 동축) — **프롭은 4.3 통과 전 결박**
```
        앞(+X)
   M1(CW상/CCW하)   M2(CCW상/CW하)
   M8 ...                 M3 ...
   M7 ...                 M4 ...
   M6(CCW상/CW하)   M5(CW상/CCW하)
        뒤(-X)
```
(정확한 ArduPilot OctoX 모터순서/회전은 P8에서 Mission Planner **Motor Test**로 검증·확정.)

### 4.3 추력 검증 (스펙 게이트: 2:1 @ 14kg)
1. **추력대(thrust stand) 또는 저울+지그**에 모터1 + 프롭1 장착.
2. 12S에서 50%/75%/100% 스로틀 정적추력 측정.
3. **합격: 단일 모터 100% ≥ 3.6 kgf → ×8 ≥ 28 kgf ≥ MTOW 14kg ×2.**
   미달이면: 프롭 피치↑ 또는 KV 재검토(BOM DR-PR-001/002 대체).

> `✅ CHECKPOINT P4`: 8모터 정적추력 합 ≥ 28kgf 실측. 모터 8개 통전·진동 정상(프롭 없이 먼저).

---

## P5. 항전 / 전원 — 하루 (천천히, 여기서 태우면 $5k 증발)

### 5.1 전원 배선 (와이어 굵기 = docs/06 §9 준수)
| 구간 | 전류 | 와이어 | 보호 |
|------|------|--------|------|
| 배터리→PDB 메인 | ~82A 연속 | **4 AWG** | **ANL 150A** + AS150 + **XT90-S 프리차지** |
| PDB→ESC ×8 | ~10A/ea | **12 AWG** | 분기 |
| PDB→BEC(5/12/19V) | — | 14~16 AWG | XT30 |
| 12V 페이로드 버스 | ~10A | **16 AWG** | 7.5~10A 퓨즈 |

1. **XT90-S(프리차지)** 먼저 결선 → 인러시 폭죽 방지. 메인은 AS150.
2. **Mauch HS-200** 파워모듈 인라인 → FC `POWER1`(I2C 전류/전압).
3. **Mauch 5.3V BEC ×2**를 다이오드 OR-ing → FC/GNSS 5V 버스(단일 BEC 고장에도 생존).
4. **6V UBEC**(서보 전용, DR-NP-004)은 **별도 버스**(로직과 분리). 12V/19V BEC은 페이로드/Jetson.

### 5.2 항전 장착
1. **Cube Orange+**: 데크 중앙, **방진 마운트**, **화살표 = 기수(+X)**. 캐리어 `POWER1`=Mauch.
2. **mosaic-X5**(주 GNSS): 상부 데크 위, **금속/고전류 멀리**, UART+I2C(컴퍼스)→FC `GPS1`.
   **Here3+**(보조): CAN `CAN1`.
3. **Jetson AGX Orin** + 캐리어: 19V, 방열판/팬. EO/IR 카메라 → Jetson(CSI/USB3). Jetson↔FC `TELEM2`(MAVLink2).
4. **RFD900x**: 드론측 `TELEM1`(57600, MAVLink2), 지상측 USB.

> `✅ CHECKPOINT P5`: 무프롭 통전 시 — FC 부팅, Mission Planner 연결, GPS fix 획득(위성≥10),
> 배터리 전압/전류 텔레메트리 표시, 연기 0.

---

## P6. 그물 페이로드 — 우리의 정체성 (1~2일)

> **단일 진실원천 [`gcs/payload_map.py`](../gcs/payload_map.py)** — 채널 절대 어기지 마라:
> **AIM-PAN=SERVO9, AIM-TILT=SERVO10, CINCH=SERVO11, RELEASE=SERVO12, NET FIRE=RELAY0(=ArduPilot RELAY1)**.

### 6.1 3D 출력 (BOM MAKE 부품)
- 출력물: PG-GIMBAL(요크/베어링), PG-SPOOL(시닝 스풀), PG-MUZZLE(머즐/베이), 포렌식 케이스.
- **프린트 설정**: PETG-CF, 노즐 0.6mm(CF는 강철노즐 필수, 황동 갈림), **벽 4겹, 인필 40% 자이로이드**,
  레이어 0.25mm. 하중 받는 요크는 **하중방향으로 레이어 눕히기**.

### 6.2 조준 짐벌 (SERVO9/10)
1. PG-GIMBAL에 **Savox SB-2290SG ×2** 장착(팬=하단 베어링축, 틸트=요크축). M3.
2. 서보혼 **중립(1500µs)에서 기계중앙** 맞춰 조립(센터 안 맞으면 P11 캘리브 지옥).
3. 머즐 노즐(PG-MUZZLE) 틸트축에. 케이블: 팬→FC **AUX1(SERVO9)**, 틸트→**AUX2(SERVO10)**.
4. **서보 전원 = 6V UBEC**(BEC, FC레일 아님). 신호 GND는 FC와 공통.

### 6.3 시닝(SERVO11) + 윈치 + 트리거
1. **시닝**: Pololu 25D 모터 + PG-SPOOL → **G2 24v13** 드라이버. 드라이버 PWM→**AUX3(SERVO11)**,
   DIR→GPIO. **INA226**(I2C)로 전류, 드로스트링을 스풀에 감아 림 둘레로 라우팅.
2. **윈치**: Pololu 37D + **G2 24v21**. **로드셀 5kg+HX711**(장력) → 페이로드 IF/FC GPIO.
3. **트리거(RELAY0)**: CO2 NC 솔레노이드 → **IRLB3034 로우사이드 MOSFET** → **아밍 릴레이 하류** →
   **플라이백 다이오드(1N5408) 병렬**. 릴레이 코일은 ArduPilot **RELAY1** 핀.
   ```
   12V ──[아밍 릴레이 NO]──┬── CO2 솔레노이드 ──┐
                           └──|◄ 1N5408 (flyback)┘
   솔레노이드(-) ── IRLB3034 D | G←FC, S←GND
   ```
4. **모든 유도부하(솔레노이드/릴레이/모터)** = 플라이백 다이오드. 빠지면 FC 리셋 → 추락쇼.

### 6.4 그물 제작 + 패킹 (차고 장인의 예술)
1. **매듭없는 Dyneema/Kevlar 메시**(셀 ~5cm), **마우스 ~3.5m**, 깊이 ~0.6m 캐스팅 네트.
2. **드로스트링(퍼스 루프)**: 마우스 둘레 채널에 Dyneema 2mm 통과 → 스풀로.
3. **림 추**: 둘레 균등 **8~16개**(브라스), 발사 시 펼침/방향성. 비대칭이면 빙글빙글.
4. **패킹(중요)**: `capture_net()`은 **발사형** → 머즐에서 사출돼 펴짐. **낙하산 패킹처럼 꼬임 없이**
   지그재그로 머즐 베이에 적재. 꼬이면 공중에서 안 펴짐 = 적 앞에서 망신.

> `✅ CHECKPOINT P6`: 짐벌 수동으로 팬/틸트 부드럽게 풀스윙(기계간섭 0). 트리거 **dry**(그물·CO2 없이)
> 릴레이 딸깍. 시닝/윈치 모터 양방향 회전. INA226/HX711 값 읽힘.

---

## P7. 하네스 / 퓨즈 / 그라운드 — 반나절

- **크림핑**: 신호=JST-GH, 전원=XT/불릿. **납땜만 ❌**(진동에 끊김) → 압착 + 열수축.
- **신호 ↔ 전원 분리**, 신호선 트위스트, SDR/짐벌 차폐. EMI = 유령 조종.
- **스타 그라운드**: 고전류 리턴과 신호 GND를 한 점에서만.
- **부팅 안전(docs/06 §10.2)**: MCU 리셋 시 모든 페이로드 출력 LOW + **아밍 릴레이 OPEN**(외부 풀다운).
- 퓨즈 전부 장착(메인 ANL 150A 포함). 케이블타이로 진동 정리(달랑거리면 끊김).

> `✅ CHECKPOINT P7`: 통전 후 연기 0, 모든 텔레메트리 정상, 페이로드 부팅 시 무동작(릴레이 OPEN 확인).

---

## P8. 펌웨어 (ArduPilot) — 여기서 "진짜 통신" 시작 (반나절)

### 8.1 플래시 & 프레임
1. Mission Planner/QGC로 Cube Orange+에 **ArduCopter 4.5+** 플래시.
2. **Frame Class = Octa, Type = X**(동축은 CoaxOcto 옵션 확인). **Motor Test**로 M1~M8 위치/회전 검증·반전.
3. 가속도/지자기/RC/배터리 모니터 캘리브레이션(Mauch 전압/전류 스케일).

### 8.2 페이로드 파라미터 (payload_map과 1:1 — 그대로 입력)
```
# 그물 짐벌/페이로드 서보 (AUX1=SERVO9 ...). FUNCTION 0 = 스크립트/MAVLink 직접 제어(RCPassthrough 대안)
SERVO9_FUNCTION  = 0      ; AIM-PAN   (DO_SET_SERVO로 직접 구동)
SERVO10_FUNCTION = 0      ; AIM-TILT
SERVO11_FUNCTION = 0      ; CINCH 드라이버 PWM
SERVO12_FUNCTION = 0      ; RELEASE
SERVO9_MIN=1000  SERVO9_MAX=2000  SERVO9_TRIM=1500     ; payload_map PWM과 일치
SERVO10_MIN=1000 SERVO10_MAX=2000 SERVO10_TRIM=1000    ; 틸트 0deg=1000
SERVO11_MIN=1000 SERVO11_MAX=2000
SERVO12_MIN=1000 SERVO12_MAX=2000
# 넷런처 발사 릴레이 (RELAY0 in payload_map == ArduPilot RELAY1)
RELAY1_FUNCTION = 1
RELAY1_PIN = 50          ; AUX 출력 핀 번호(보드/펌웨어 버전에 맞게 확인)
# 수동 조종 / 페일세이프
BRD_SAFETY_DEFLT = 0     ; 세이프티 스위치 정책(운용규정 따라)
FENCE_ENABLE = 1  FENCE_TYPE = 7  FENCE_RADIUS = 300  FENCE_ALT_MAX = 120
FS_THR_ENABLE = 1  FS_GCS_ENABLE = 1   ; 링크두절 → RTL → LAND
# 텔레메트리/보안
SERIAL1_PROTOCOL = 2  SERIAL1_BAUD = 57   ; TELEM1 = RFD900x, MAVLink2
SERIAL2_PROTOCOL = 2                      ; TELEM2 = Jetson
```
> ⚠️ `RELAYx_PIN`/`SERVOx_FUNCTION` 핀번호는 **펌웨어/보드 버전마다 다름** — Mission Planner의
> 드롭다운/`BRD_PWM_*`로 실제 사용 가능한 핀 확인 후 입력. payload_map 채널(9/10/11/12)·릴레이(RELAY1) **숫자**만 고정.

### 8.3 인터록(권장)
실제 발사 인터록(아밍∧조준완료∧고도)은 **ArduPilot Lua 스크립트** 또는 페이로드 IF MCU에서 강제.
초기 벤치에선 콕핏의 SW 인터록(`gcs.control`: ARM 전 FIRE 거부)으로 충분.

> `✅ CHECKPOINT P8`: Mission Planner Servo Output 화면에서 SERVO9~12 슬라이더로 짐벌/시닝이 **물리적으로 움직임**.
> 릴레이 토글로 트리거 dry 작동.

---

## P9. 포렌식 기기 "ForensIQ-1" 빌드 — 하루 (드론보다 쉬움)

1. **케이스**: `cad/forensic_appliance.scad` → STL → PETG/ASA 출력. 키락·탬퍼씰.
   ```bash
   openscad -o /tmp/forensiq.stl cad/forensic_appliance.scad   # Simple: yes 확인됨
   ```
2. **전장 조립**(전부 케이스 내부 마운트):
   - **CM4 + Waveshare 캐리어** → **NVMe SSD**(M.2) → **7" DSI 터치**(FPC) →
   - **하드웨어 write-blocker(USB) + SD 리더**(전면 슬롯 = **증거 카드 전용**) →
   - **80mm 열전사 프린터**(패널, USB/TTL) → **UPS HAT + 18650 ×2** → **DS3231 RTC**(I2C) →
   - 전면 LED/START/EJECT/키락, 후면 **WORM USB**·이더넷·전원인렛.
3. **OS/소프트웨어 굽기**:
   ```bash
   # CM4에 Raspberry Pi OS (64-bit), NVMe 부팅. 그 위에:
   sudo apt install -y exiftool dc3dd sleuthkit binwalk python3-pip
   pip install -r requirements-forensics.txt    # pymavlink pyulog pynmea2 gpxpy folium fpdf2
   python3 -c "import forensics; print('forensics ready')"
   ```
4. **에어갭**: WiFi 끔, 이더넷만(서명 업데이트/증거 내보내기용).

> `✅ CHECKPOINT P9`: 터치 부팅, write-blocker 자가테스트 녹색, 열전사 용지 급지 OK,
> `import forensics` 성공.

---

## P10. 소프트웨어 브링업 — 실제 통신 확인 (1시간)

### 10.1 무하드웨어 풀루프 (먼저 — 실 MAVLink)
지상국 노트북에서:
```bash
pip install -r requirements-gcs.txt          # pygame numpy pymavlink
# 터미널 1: 차량 에뮬레이터(실 MAVLink2 프레임)
python -m gcs.sim_vehicle --connect udpin:127.0.0.1:14550
# 터미널 2: 콕핏
python -m gcs --connect udpout:127.0.0.1:14550
```
**기대 결과(HUD)**: 좌상단 `LINK: MAVLINK ...` **녹색**, 자세/배터리/GPS 라이브, 하단 `LINK LIVE`.
`G`로 ARM(상태바 ARMED), `IJKL`로 NET 레티클 이동, `SPACE`로 `FIRE_NET` 토스트.

### 10.2 실 FC 연결
```bash
python -m gcs --connect /dev/ttyACM0                 # USB 직결
python -m gcs --connect udpout:<radio-host>:14550    # RFD900x/네트워크
python -m gcs --connect /dev/ttyACM0 --video rtsp://<eo-ip>:8554/eo   # + 실 EO 피드
```

> `✅ CHECKPOINT P10`: 실 FC에서 HUD에 **실 자세/GPS/배터리**, 콕핏 ARM/조준 명령이 FC 로그/Servo
> Output에 도달. (배포 상세: [docs/11](11_CONOPS_and_Deployment.md))

---

## P11. 서보 캘리브레이션 — "코드 = 쇠" 일치 (1시간, 핵심)

목표: **콕핏이 보내는 각도 = 짐벌의 실제 각도**. (각도기/디지털 인클리노미터 준비)

1. 콕핏 `J`/`L`로 **팬 중립(0°)** 명령 → 짐벌이 정중앙 아니면 **`SERVO9_TRIM`** 조정.
2. 팬 **+60°** 명령(payload_map: 2000µs) → 각도기로 실측. 60°와 다르면 **`SERVO9_MAX`** 미세조정.
   **−60°**(1000µs) → **`SERVO9_MIN`**. (`SERVO9_REVERSED`로 방향 반전)
3. 틸트(SERVO10) 동일: 0°=1000µs(TRIM/MIN), 75°=2000µs(MAX). 기계 엔드스톱 전에서 멈추게.
4. **소프트 리밋 = payload_map(−60..60 / 0..75)** 안에서만 움직이는지 재확인.
5. 결과를 Mission Planner에서 저장(param 백업).

> `✅ CHECKPOINT P11`: 콕핏 명령 0/±60(팬), 0/75(틸트) → **실측 오차 ≤ ±2°**. 엔드스톱 충돌 0.

---

## P12. 벤치 테스트 매트릭스 — 합격/불합격 (반나절)

> **프롭 OFF, 그물 OFF(dry), 2인.** 통과 못 하면 비행 금지.

| # | 테스트 | 명령/방법 | 합격 기준 |
|---|--------|-----------|-----------|
| 1 | 부팅 안전 | 전원 인가, 멀티미터로 RELAY1/게이트 | 출력 LOW, 릴레이 OPEN |
| 2 | 텔레메트리 | `python -m gcs --connect ...` | HUD 실 자세/GPS/배터리, `LINK LIVE` |
| 3 | **조준** | 콕핏 `IJKL` | 짐벌이 명령각 ±2° 추종(P11) |
| 4 | 아밍 인터록 | `SPACE` 먼저 → `G` → `SPACE` | ARM 전 `DENIED`, ARM 후 `FIRE_NET` |
| 5 | E-Stop | `B` | 즉시 DISARM, throttle 0, 릴레이 OPEN |
| 6 | **발사(dry)** | `G`→`SPACE` | RELAY1 ON 펄스, 솔레노이드 딸깍(그물·CO2 없이) |
| 7 | 시닝 | `C` | 스풀 권취, INA226 전류상승→임계서 정지 |
| 8 | 윈치 | recover | 권취/정지, 과장력(로드셀) 자동정지 |
| 9 | 추력마진 | P4 재확인 | ≥28kgf |
| 10 | **포렌식 E2E** | 아래 코드 | 샘플 카드→**열전사 리포트 출력** |

**#10 빠른 검증(샘플 ArduPilot 로그 생성→리포트):**
```bash
python3 - <<'PY'
import os,tempfile
from forensics import ForensicAppliance
card=tempfile.mkdtemp()
open(os.path.join(card,"L.nmea"),"w").write("$GPGGA,120000,3730.00,N,12700.00,E,1,09,0.9,120,M,0,M,,*5C\n")
rep,coc=ForensicAppliance(work_dir=tempfile.mkdtemp()).process_card(
  "EV-BENCH",card,"op","bench card")
print("PDF:",rep.pdf_path,"| launch:",rep.findings.launch_estimate,"| CoC ok:",coc.verify())
PY
```
기대: PDF 생성 + 발사지점 좌표 + CoC verify True. (실기에선 write-blocked 슬롯 카드 → 열전사 인쇄)

> `✅ CHECKPOINT P12`: 10개 전부 PASS.

---

## P13. 통합 & 비행시험 사다리 (단계적, 절대 건너뛰기 금지)

1. **SITL/HIL 리허설**: `sim_vehicle.py -v ArduCopter` ↔ 콕핏으로 미션 흐름
   (조준→아밍→발사→시닝→투하→RTL) 손에 익히기.
2. **테더드 호버**: 마당에서 끈 묶고 저고도 호버 30초 → 진동(VIBE)/온도/전류 로그 확인. **링크 끊어보기**(페일세이프 RTL/LAND).
3. **그물 야외 발사시험(무인지대)**: 풍선/저가 테스트 드론 표적 → `IJKL` 조준 → `G`→`SPACE` 발사 →
   **전개·포획·시닝** 실측. 안 잡히면 조준 오프셋/발사 타이밍/패킹 튜닝.
4. **자유비행**: 단계적 고도/거리 확장. **매 비행 후 나사·커넥터·배터리 재점검**(진동이 다 푼다).

> `✅ CHECKPOINT P13`: 테더 호버 안정, 페일세이프 동작, 그물 표적 포획 1회 이상 성공.

---

## P14. 트러블슈팅 (차고 장인 눈물의 FAQ)

| 증상 | 범인 | 처방 |
|------|------|------|
| 짐벌이 반대로/덜 돈다 | 방향/리밋 | `SERVO9_REVERSED`, MIN/MAX 재조정(P11) |
| 콕핏 `OFFLINE`만 | udp 방향/방화벽 | GCS=`udpout:`, 차량/SITL=`udpin:`. 포트 14550 |
| FIRE 안 나감 | 아밍/조준 인터록 | `G`로 ARM, dry로 RELAY1부터 확인 |
| 부팅하면 모터 춤 | 플라이백 누락/EMI | 다이오드, 신호선 분리·트위스트 |
| GPS fix 안 잡힘 | mosaic 배치/간섭 | 고전류·금속서 멀리, 하늘 시야 확보 |
| 그물 안 펴짐 | 패킹 꼬임/추 비대칭 | 낙하산식 재패킹, 림 추 대칭화 |
| Jetson 화남(뜨거움) | 방열 부족 | 써멀패드/팬, `nvpmodel` 클럭제한 |
| 열전사 백지 | 용지 방향 | 감열면 바깥으로 재급지 |
| VIBE 빨강/Clipping | 진동 | FC 방진마운트, 프롭 밸런싱, 암 강성 |
| 옆집 김씨 또 옴 | CO2 발사음 | 더 먼 곳 + 야식 회유(검증된 외교) |

---

## P15. DONE 체크리스트 (= "진짜 작동" 정의)

- [ ] BOM 70라인 조달/외주/차고제작 완료(완성품 2개).
- [ ] 드론: 추력 ≥2:1, MTOW 14kg 내, 전원/퓨즈 docs/06대로, 페일세이프 RTL/LAND 검증.
- [ ] **페이로드: 조준(SERVO9/10)·시닝(11)·릴리스(12)·발사(RELAY0) 전부 콕핏에서 실동작.**
- [ ] **콕핏↔FC 실 MAVLink 통신**(HUD 실 텔레메트리, 명령 도달).
- [ ] **payload_map 각도 = 실 짐벌 각도(±2°)** 캘리브 완료.
- [ ] 그물 야외 발사·전개·포획 1회+ 성공.
- [ ] **ForensIQ-1: 카드→이미징→해시→파싱→발사지점→열전사 리포트** 실동작.
- [ ] 안전: 2인·E-Stop·LiPo/CO2 수칙·합법 공역/허가 확인.

> 다 체크되면 — 축하한다. 당신은 **차고에서 대드론 체계 2개를 손으로 만들어 소프트웨어로
> 굴리는 사람**이다. 옆집 김씨에겐 "RC 취미"라고 해둬라.
>
> 한 줄: **부품은 BOM, 형상은 SCAD, 통신은 gcs↔MAVLink, 영혼은 차고. 키보드로 그물을 쏜다.**
