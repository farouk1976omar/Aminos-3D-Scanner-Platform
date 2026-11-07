import streamlit as st
import os
import sqlite3
import operator
import time
import uuid
from PIL import Image
from typing import TypedDict, List, Annotated
from dotenv import load_dotenv

# تحميل المتغيرات من ملف .env تلقائياً
load_dotenv()

import google.generativeai as genai
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

# استدعاء Tavily بشكل آمن
try:
    from tavily import TavilyClient
    TAVILY_AVAILABLE = True
except ImportError:
    TAVILY_AVAILABLE = False

# ==========================================
# 1. الإعدادات ومفاتيح API (Pre-flight Validation)
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def get_secret(key_name: str) -> str:
    """جلب المفاتيح من بيئة العمل أو من أسرار Streamlit Cloud بأمان"""
    val = os.environ.get(key_name, "")
    if not val and hasattr(st, "secrets") and key_name in st.secrets:
        val = str(st.secrets[key_name])
    return val.strip()

GEMINI_API_KEY = get_secret("GEMINI_API_KEY")
TAVILY_API_KEY = get_secret("TAVILY_API_KEY")

# إعداد نموذج Gemini مع دعم الموديلات الأحدث تلقائياً
flash_model = None
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # تفضيل أحدث نموذج متاح ومستقر
        for model_name in ['gemini-3.8-flash', 'gemini-2.5-flash', 'gemini-flash-latest', 'gemini-1.5-flash']:
            try:
                flash_model = genai.GenerativeModel(model_name)
                break
            except Exception:
                continue
    except Exception as e:
        st.warning(f"⚠️ خطأ في تهيئة مكتبة Google GenAI: {e}")

# ==========================================
# 2. هيكل الحالة المشتركة للوكلاء (Shared State)
# ==========================================
class ScannerProjectState(TypedDict):
    target_technology: str
    patents_and_papers: Annotated[List[str], operator.add]
    hardware_components: Annotated[List[dict], operator.add]
    extracted_pcb_images: Annotated[List[str], operator.add]
    circuit_design: str
    physics_calculations: str
    dsp_algorithms: str
    firmware_code: str
    design_status: str

# ==========================================
# 3. الدوال المساعدة والحماية (Tools & Retry Logic)
# ==========================================
def generate_with_retry(prompt: str, image=None, retries: int = 3, delay: int = 2) -> str:
    """دالة الاتصال بـ Gemini مع إعادة المحاولة التلقائية وتجربة الموديلات المتاحة"""
    candidate_models = ['gemini-3.8-flash', 'gemini-flash-latest', 'gemini-2.5-flash', 'gemini-1.5-flash']
    
    for model_name in candidate_models:
        for attempt in range(retries):
            try:
                m = genai.GenerativeModel(model_name)
                if image:
                    response = m.generate_content([prompt, image])
                else:
                    response = m.generate_content(prompt)
                if response and hasattr(response, 'text') and response.text:
                    return response.text
            except Exception as e:
                err_str = str(e)
                if "404" in err_str or "not found" in err_str.lower() or "no longer available" in err_str.lower():
                    # الانتقال للنموذج التالي مباشرة
                    break
                if attempt < retries - 1:
                    time.sleep(delay)
                else:
                    continue
    return "[-] تعذر الحصول على رد من نماذج الذكاء الاصطناعي بعد تجربة كافة الخيارات المتاحة."

def official_search_tool(query: str) -> str:
    """البحث الرسمي باستخدام Tavily المخصص لوكلاء الذكاء الاصطناعي"""
    if not TAVILY_AVAILABLE or not TAVILY_API_KEY:
        return f"⚠️ محرك بحث Tavily غير مفعل. استعلام البحث الموجه: {query}"
    try:
        tavily = TavilyClient(api_key=TAVILY_API_KEY)
        response = tavily.search(query=query, search_depth="advanced", max_results=3)
        results = [f"- {res.get('title', 'مرجع')}: {res.get('content', '')}" for res in response.get('results', [])]
        return "\n".join(results) if results else "لم يتم العثور على أبحاث كافية."
    except Exception as e:
        return f"[-] خطأ في محرك بحث Tavily: {e}"

# ==========================================
# 4. وكلاء الذكاء الاصطناعي المتخصصون (AI Agents)
# ==========================================
def research_agent(state: ScannerProjectState):
    tech = state.get("target_technology", "3D_Scanner")
    pcb_images = state.get("extracted_pcb_images", [])
    
    queries = {
        "3D_Scanner": "Fluxgate Gradiometer 3D Ground Scanner patent hardware FLC100", 
        "PI": "Pulse Induction metal detector coil damping delay time patent fast decay", 
        "VLF": "Very Low Frequency metal detector inductive balance phase shift patent nulling",
        "GPR": "Ground Penetrating Radar Bowtie antenna nanosecond pulse UWB transceiver patent"
    }
    raw_text = official_search_tool(queries.get(tech, "metal detector"))
    
    research_prompt = f"أنت مهندس R&D وخبير براءات اختراع. استخلص الأسرار الهندسية لتقنية ({tech}) بناءً على بيانات البحث التالية:\n{raw_text}"
    research_report = generate_with_retry(research_prompt)
    
    if pcb_images and pcb_images[-1]:
        try:
            img = Image.open(pcb_images[-1])
            vision_prompt = "أنت مهندس إلكترونيات عكسية. قم بتحليل هذه اللوحة (PCB): استخرج أرقام الرقائق (ICs)، تنظيم الطاقة، وأماكن الحساسات ومسارات الإشارة."
            vision_report = generate_with_retry(vision_prompt, image=img)
            research_report += f"\n\n### 🔍 تحليل اللوحة المرفوعة بالرؤية الحاسوبية:\n{vision_report}"
        except Exception as e:
            research_report += f"\n\n[-] تعذر تحليل الصورة: {e}"

    base_components = [{"part": "ESP32-WROOM-32", "type": "Microcontroller"}]
    if tech == "3D_Scanner":
        base_components.extend([
            {"part": "FLC-100 x2", "type": "Fluxgate Magnetometer Sensors"},
            {"part": "ADS1115", "type": "16-Bit Precision ADC (I2C)"},
            {"part": "SSD1306 1.3 OLED", "type": "Display (I2C)"},
            {"part": "MicroSD Socket", "type": "SPI Data Logger"}
        ])
    elif tech == "PI":
        base_components.extend([
            {"part": "IRF740 / IRF640", "type": "High-Voltage Power MOSFET"},
            {"part": "NE5534 / TL072", "type": "Ultra-Low Noise Fast Op-Amp"}
        ])
    elif tech == "VLF":
        base_components.extend([
            {"part": "TX & RX Search Coils", "type": "Inductive Balanced Resonant Coils"},
            {"part": "Synchronous Demodulator IC", "type": "I/Q Phase Detector"}
        ])
    elif tech == "GPR":
        base_components.extend([
            {"part": "UWB Pulse Generator", "type": "Avalanche / Step Recovery Diode"},
            {"part": "Bowtie Antenna Pair", "type": "Wideband TX/RX Antennas"}
        ])
    
    return {
        "patents_and_papers": [research_report], 
        "hardware_components": base_components, 
        "design_status": f"تمت أبحاث تقنية {tech} بنجاح"
    }

def hardware_agent(state: ScannerProjectState):
    components = state.get("hardware_components", [])
    tech = state.get("target_technology", "3D_Scanner")
    prompt = f"أنت مهندس إلكترونيات وتصميم دوائر (Hardware Architect). صمم دائرة آمنة لربط القطع التالية: {components} المخصصة لتقنية ({tech}). ركز على تنظيم الجهد (3.3V / 5V)، عزل الضوضاء الأرضية (GND Isolation)، واختيار المكثفات المناسبة لتفادي التشويش."
    return {"circuit_design": generate_with_retry(prompt), "design_status": "المخطط الكهربائي مكتمل"}

def physics_3d_agent(state: ScannerProjectState):
    circuit = state.get("circuit_design", "")
    prompt = f"أنت خبير جيوفيزياء ومغناطيسية أرضية. بناءً على المخطط:\n{circuit[:800]}\nحدد المسافة الهندسية الدقيقة لمعايرة 2 حساس فلكس جيت (FLC-100) كـ Gradiometer رأسي لقياس التدرج المغناطيسي، وكيفية إلغاء المجال المغناطيسي للأرض وكشف التجاويف والمعادن الدفينة."
    return {"physics_calculations": generate_with_retry(prompt), "design_status": "الحسابات الفيزيائية للماسح 3D جاهزة"}

def physics_pi_agent(state: ScannerProjectState):
    prompt = "أنت جيوفيزيائي متخصص بكواشف الحث النبضي (PI). صمم ملف البحث النحاسي: احسب الحث بالميكروهنري (Inductance µH)، المقاومة الداخلية، عرض النبضة (Pulse Width)، زمن التأخير (Sample Delay µs)، ومقاومة التخميد الحرجة (Critical Damping Resistor) لمنع الرنين العكسي."
    return {"physics_calculations": generate_with_retry(prompt), "design_status": "فيزياء الحث النبضي PI جاهزة"}

def physics_vlf_agent(state: ScannerProjectState):
    prompt = "أنت جيوفيزيائي متخصص بكواشف التردد المنخفض (VLF). صمم ملفات الإرسال والاستقبال (TX/RX). اشرح كيفية ضبط التوازن الحثي الدقيق (Coil Nulling < 10mV) وحساب انزياح الطور (Phase Shift) لتمييز الذهب والفضة والحديد بدقة."
    return {"physics_calculations": generate_with_retry(prompt), "design_status": "فيزياء VLF والتوازن الحثي جاهزة"}

def physics_gpr_agent(state: ScannerProjectState):
    prompt = "أنت مهندس RF وجيوفيزيائي راداري (GPR). صمم نظام رادار اختراق أرضي بنبضات النانو ثانية (UWB Sub-nanosecond Pulses)، وهوائيات Bowtie، وكيفية حساب معامل السماحية الكهربائية (Dielectric Permittivity) لتربات مختلفة لتقدير عمق الأهداف بدقة بالسنتيمتر."
    return {"physics_calculations": generate_with_retry(prompt), "design_status": "فيزياء رادار الاختراق الأرضي GPR جاهزة"}

def dsp_agent(state: ScannerProjectState):
    tech = state.get("target_technology", "3D_Scanner")
    physics = state.get("physics_calculations", "")
    
    if tech == "PI":
        prompt = f"أنت خبير معالجة الإشارات الرقمية (DSP) لكواشف PI. بناءً على فيزياء الملف:\n{physics[:800]}\nاكتب خوارزمية تكامل الإشارة (Signal Integration)، التصفية بمتوسط متحرك (Moving Average)، وطرح ضوضاء الأرض الساكنة."
    elif tech == "VLF":
        prompt = f"أنت خبير DSP لكواشف VLF. بناءً على فيزياء التوازن الحثي:\n{physics[:800]}\nاكتب خوارزمية فك التضمين المتزامن (I/Q Demodulation) لحساب المركبة الحقيقية والخيالية (Real/Imaginary) وزاوية الطور (Phase Angle)."
    elif tech == "GPR":
        prompt = f"أنت خبير DSP لرادار GPR. بناءً على فيزياء النبضات:\n{physics[:800]}\nاكتب خوارزمية معالجة B-Scan، فلترة خلفية الأرض (Background Removal)، ومطابقة الفاصل الزمني للنبضات (Time-Gain Compensation)."
    else:
        prompt = f"أنت خبير DSP لماسحات 3D المغناطيسية. بناءً على فيزياء التدرج:\n{physics[:800]}\nاكتب خوارزمية طرح قراءات الحساسين التفاضلية (Differential Subtraction)، الفلترة الرقمية لتردد 50/60Hz، ومصفوفة الشبكة (Grid Interpolation) للرسم ثلاثي الأبعاد."
        
    return {"dsp_algorithms": generate_with_retry(prompt), "design_status": f"خوارزميات DSP لتقنية {tech} جاهزة"}

def firmware_agent(state: ScannerProjectState):
    tech = state.get("target_technology", "3D_Scanner")
    dsp = state.get("dsp_algorithms", "")
    prompt = f"أنت مبرمج أنظمة مدمجة (Embedded Firmware Engineer). اكتب كود C++ نظيف وقابل للبناء مباشرة على متحكم ESP32 (Arduino Framework) لتنفيذ خوارزميات الـ DSP التالية:\n{dsp[:1200]}\nاستخدم مؤقتات الهاردوير الدقيقة (Hardware Timers / Interrupts)، وقراءة النواقل بسرعة، وإرسال البيانات بصيغة مجهزة للواجهة."
    return {"firmware_code": generate_with_retry(prompt), "design_status": "تم الانتهاء من كتابة كود التشغيل (Firmware)"}

def routing_logic(state: ScannerProjectState) -> str:
    tech = state.get("target_technology")
    if tech == "PI":
        return "Physics_PI"
    elif tech == "VLF":
        return "Physics_VLF"
    elif tech == "GPR":
        return "Physics_GPR"
    return "Physics_3D"

# ==========================================
# 5. بناء وتجميع مسار العمل (LangGraph Workflow)
# ==========================================
@st.cache_resource
def build_workflow():
    workflow = StateGraph(ScannerProjectState)
    
    workflow.add_node("Research", research_agent)
    workflow.add_node("Hardware", hardware_agent)
    workflow.add_node("Physics_3D", physics_3d_agent)
    workflow.add_node("Physics_PI", physics_pi_agent)
    workflow.add_node("Physics_VLF", physics_vlf_agent)
    workflow.add_node("Physics_GPR", physics_gpr_agent)
    workflow.add_node("DSP", dsp_agent)
    workflow.add_node("Firmware", firmware_agent)
    
    workflow.set_entry_point("Research")
    workflow.add_edge("Research", "Hardware")
    workflow.add_conditional_edges("Hardware", routing_logic)
    
    workflow.add_edge("Physics_3D", "DSP")
    workflow.add_edge("Physics_PI", "DSP")
    workflow.add_edge("Physics_VLF", "DSP")
    workflow.add_edge("Physics_GPR", "DSP")
    
    workflow.add_edge("DSP", "Firmware")
    workflow.add_edge("Firmware", END)
    
    db_path = os.path.join(BASE_DIR, "agents_memory.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    memory = SqliteSaver(conn)
    return workflow.compile(checkpointer=memory)

# ==========================================
# 6. واجهة المستخدم التفاعلية (Streamlit UI)
# ==========================================
st.set_page_config(page_title="منصة الذكاء الاصطناعي لكواشف المعادن والماسحات 3D", page_icon="📡", layout="wide")
st.title("📡 منصة الوكلاء الأذكياء لتصميم وتطوير كواشف المعادن والماسحات ثلاثية الأبعاد")

# التحقق من مفاتيح التشغيل
if not GEMINI_API_KEY:
    st.error("🚨 مفتاح GEMINI_API_KEY غير موجود في ملف .env أو في متغيرات النظام! يرجى إضافته إلى ملف `.env`.")
    st.info("💡 يمكنك نسخ الملف `.env.example` إلى `.env` وإضافة مفتاحك من Google AI Studio.")
    st.stop()

if not TAVILY_API_KEY:
    st.warning("ℹ️ مفتاح TAVILY_API_KEY غير متوفر. سيقوم وكيل الأبحاث بالعمل بالاستناد إلى المعرفة الهندسية المدمجة لـ Gemini.")

with st.sidebar:
    st.header("⚙️ إعدادات المشروع")
    tech_options = {
        "3D_Scanner": "ماسح أرضي مغناطيسي ثلاثي الأبعاد (Fluxgate Gradiometer 3D)",
        "PI": "كاشف حث نبضي للأعماق الكبيرة (Pulse Induction - PI)",
        "VLF": "كاشف تردد منخفض مع تمييز المعادن (VLF Metal Detector)",
        "GPR": "رادار اختراق الأرض بنبضات النانو (Ground Penetrating Radar)"
    }
    selected_key = st.selectbox("اختر تقنية الجهاز المطلوب:", list(tech_options.keys()), format_func=lambda x: f"{x} - {tech_options[x]}")
    uploaded_file = st.file_uploader("🖼️ رفع صورة بوردة (PCB) للهندسة العكسية:", type=["jpg", "jpeg", "png"])
    
    st.markdown("---")
    if st.button("🔄 توليد جلسة عمل جديدة"):
        st.session_state['thread_id'] = f"proj_{str(uuid.uuid4())[:8]}"
        
    if 'thread_id' not in st.session_state:
        st.session_state['thread_id'] = f"proj_{str(uuid.uuid4())[:8]}"
        
    st.text_input("معرف جلسة الوكلاء (Thread ID):", value=st.session_state['thread_id'], disabled=True)
    start_btn = st.button("🚀 إطلاق فريق المهندسين الآليين", type="primary", use_container_width=True)

# منطقة تنفيذ المهام التفاعلية
if start_btn:
    saved_img = None
    if uploaded_file:
        upload_dir = os.path.join(BASE_DIR, "uploaded_pcbs")
        os.makedirs(upload_dir, exist_ok=True)
        saved_img = os.path.join(upload_dir, uploaded_file.name)
        with open(saved_img, "wb") as f:
            f.write(uploaded_file.getbuffer())
        st.sidebar.success(f"تم حفظ الصورة: {uploaded_file.name}")

    app = build_workflow()
    config = {"configurable": {"thread_id": st.session_state['thread_id']}}
    
    initial_state = {
        "target_technology": selected_key,
        "patents_and_papers": [],
        "hardware_components": [],
        "extracted_pcb_images": [saved_img] if saved_img else [],
        "circuit_design": "",
        "physics_calculations": "",
        "dsp_algorithms": "",
        "firmware_code": "",
        "design_status": "بدء دورة التصميم والتحليل"
    }
    
    st.info(f"[*] تم استدعاء الوكلاء لتصميم وتطوير نظام: **{selected_key} - {tech_options[selected_key]}**")
    progress_bar = st.progress(0)
    
    step = 0
    total_steps = 5
    
    for event in app.stream(initial_state, config):
        for node_name, state_update in event.items():
            step += 1
            progress_bar.progress(min(int((step / total_steps) * 100), 100))
            
            with st.expander(f"✅ اكتمل: {node_name} | الحالة: {state_update.get('design_status', '')}", expanded=True):
                if "patents_and_papers" in state_update and state_update["patents_and_papers"]:
                    st.markdown("### 📚 الأبحاث وبراءات الاختراع والهندسة العكسية")
                    st.write(state_update["patents_and_papers"][-1])
                if "circuit_design" in state_update:
                    st.markdown("### 🔌 المخطط الإلكتروني وتوزيع المكونات")
                    st.write(state_update["circuit_design"])
                if "physics_calculations" in state_update:
                    st.markdown("### 🧲 الحسابات الفيزيائية والكهرومغناطيسية")
                    st.write(state_update["physics_calculations"])
                if "dsp_algorithms" in state_update:
                    st.markdown("### 📊 خوارزميات المعالجة الرقمية للإشارة (DSP)")
                    st.write(state_update["dsp_algorithms"])
                if "firmware_code" in state_update:
                    st.markdown("### 💻 كود التشغيل المضمن (ESP32 Firmware C++)")
                    st.code(state_update["firmware_code"], language="cpp")

    st.success("🎉 اكتملت دورة التصميم بنجاح! تم حفظ كافة الحالات في قاعدة البيانات.")
    
    # استخراج وتنزيل التقرير الهندسي الشامل
    final_state = app.get_state(config).values
    report_md = f"""# 📁 التقرير الهندسي الشامل: {selected_key} ({tech_options[selected_key]})
تاريخ التقرير: {time.strftime('%Y-%m-%d %H:%M:%S')}
معرف الجلسة: {st.session_state['thread_id']}

---

## 1. الأبحاث وبراءات الاختراع والهندسة العكسية
{final_state.get('patents_and_papers', [''])[-1]}

---

## 2. المخطط الإلكتروني وتوزيع المكونات
{final_state.get('circuit_design', '')}

---

## 3. الحسابات الفيزيائية والكهرومغناطيسية
{final_state.get('physics_calculations', '')}

---

## 4. خوارزميات المعالجة الرقمية للإشارة (DSP)
{final_state.get('dsp_algorithms', '')}

---

## 5. كود التشغيل المضمن (ESP32 Firmware C++)
```cpp
{final_state.get('firmware_code', '')}
```
"""
    st.markdown("---")
    st.download_button(
        label=f"📥 تحميل التقرير الهندسي الكامل ({selected_key}_Design_Document.md)",
        data=report_md,
        file_name=f"{selected_key}_Design_Document.md",
        mime="text/markdown",
        type="primary"
    )
