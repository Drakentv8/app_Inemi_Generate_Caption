from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import os
import time
import logging
from datetime import datetime, timedelta
import json
from collections import defaultdict
import statistics

app = Flask(__name__)
CORS(app)

# Konfigurasi Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Cache dan storage
caption_cache = {}
performance_data = defaultdict(list)
hashtag_trends = defaultdict(lambda: defaultdict(int))
posting_time_stats = defaultdict(lambda: defaultdict(list))

# Konfigurasi NVIDIA API
client = OpenAI(api_key="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", base_url="https://integrate.api.nvidia.com/v1")

@app.route('/')
def index():
    return render_template('index.html')

def generate_ai_caption(topik, gaya, platform, bahasa="indonesia"):
    cache_key = f"{topik}_{gaya}_{platform}_{bahasa}"
    
    # Cek cache terlebih dahulu
    if cache_key in caption_cache:
        logger.info("Menggunakan hasil dari cache")
        return caption_cache[cache_key]
    
    prompt = f"""
    Buatkan caption viral untuk platform {platform} dengan:
    - Topik: {topik}
    - Gaya: {gaya}
    - Bahasa: {bahasa}
    
    Format output HARUS dalam dictionary Python:
    {{
        "hook": "kalimat pembuka menarik (max 10 kata)",
        "caption": "isi utama (2-3 kalimat)",
        "cta": "call to action kreatif",
        "hashtags": "5 hashtag relevan",
        "tips": "2 tips untuk meningkatkan engagement"
    }}
    
    Contoh untuk gaya promosi:
    - Hook: "Skincare murah tapi luxury feel!"
    - Caption: "Cuma 50rb bisa dapet glowing kayak artis. Udah tested 1000+ customer!"
    - CTA: "DM 'GLOW' untuk info lengkap!"
    - Hashtags: "#skincareviral #glowingcheck #beautytips #fyp #umkmindonesia"
    - Tips: "1. Pakai transition effect sebelum-after\n2. Tag 3 temen di komen"
    """
    
    try:
        start_time = time.time()
        
        response = client.chat.completions.create(
            model="nvidia/llama-3.3-nemotron-super-49b-v1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            top_p=0.95,
            max_tokens=4096,
            frequency_penalty=0,
            presence_penalty=0
        )
        
        # Parse the response content
        content = response.choices[0].message.content.strip()
        
        # Try to extract the dictionary from the response
        try:
            # Find the dictionary in the response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No dictionary found in response")
            
            dict_str = content[start_idx:end_idx]
            generated_content = eval(dict_str)
            
            # Validate the required fields
            required_fields = ['hook', 'caption', 'cta', 'hashtags', 'tips']
            if not all(field in generated_content for field in required_fields):
                raise ValueError("Missing required fields in response")
            
            # Add metadata
            generated_content.update({
                "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "platform": platform,
                "style": gaya,
                "language": bahasa
            })
            
            # Simpan ke cache
            caption_cache[cache_key] = generated_content
            
            logger.info(f"Generasi caption selesai dalam {time.time()-start_time:.2f} detik")
            return generated_content
            
        except Exception as e:
            logger.error(f"Error parsing AI response: {str(e)}")
            # Return a default response if parsing fails
            return {
                "hook": "Caption menarik untuk kontenmu!",
                "caption": "Buat konten yang menarik dan informatif untuk audiensmu.",
                "cta": "Jangan lupa like dan follow untuk konten lebih menarik!",
                "hashtags": "#viral #trending #fyp #contentcreator #viralcontent",
                "tips": "1. Gunakan musik yang trending\n2. Tambahkan efek visual yang menarik",
                "error": "Gagal memproses respons AI, menggunakan template default"
            }
        
    except Exception as e:
        logger.error(f"Error dalam generasi caption: {str(e)}")
        return {
            "error": "Gagal membuat caption",
            "detail": str(e)
        }

@app.route('/generate_caption', methods=['POST'])
def generate_caption():
    try:
        data = request.get_json()
        
        # Validasi input
        required_fields = ['topik', 'gaya', 'platform']
        if not all(field in data for field in required_fields):
            return jsonify({"error": "Data tidak lengkap"}), 400
            
        topik = data['topik'].strip()
        if len(topik) < 3:
            return jsonify({"error": "Topik terlalu pendek"}), 400
            
        # Parameter opsional
        bahasa = data.get('bahasa', 'indonesia')
        
        result = generate_ai_caption(
            topik=data['topik'],
            gaya=data['gaya'],
            platform=data['platform'],
            bahasa=bahasa
        )
        
        if 'error' in result:
            return jsonify(result), 500
            
        return jsonify(result)
        
    except Exception as e:
        logger.exception("Error dalam endpoint generate_caption")
        return jsonify({
            "error": "Terjadi kesalahan server",
            "detail": str(e)
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "cache_size": len(caption_cache)
    })

def analyze_hashtag_trends(platform):
    """Analisis trending hashtags untuk platform tertentu menggunakan AI"""
    try:
        # Prompt untuk AI untuk menganalisis trending hashtags
        prompt = f"""
        Analisis trending hashtags untuk platform {platform} saat ini.
        Berikan 5 hashtag paling trending dengan format:
        {{
            "hashtags": [
                {{
                    "tag": "nama_hashtag",
                    "count": jumlah_penggunaan,
                    "trend": "up/down/stable",
                    "context": "konteks penggunaan",
                    "audience": "target audience",
                    "engagement_rate": "tingkat engagement"
                }}
            ],
            "analysis": "analisis singkat tentang trend hashtag",
            "recommendation": "rekomendasi penggunaan"
        }}
        
        Fokus pada:
        1. Hashtag yang sedang viral
        2. Relevansi dengan platform {platform}
        3. Potensi engagement
        4. Target audience
        5. Konteks penggunaan
        """
        
        # Panggil AI untuk analisis
        response = client.chat.completions.create(
            model="nvidia/llama-3.3-nemotron-super-49b-v1",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            top_p=0.95,
            max_tokens=4096,
            frequency_penalty=0,
            presence_penalty=0
        )
        
        # Parse response AI
        content = response.choices[0].message.content.strip()
        
        try:
            # Extract dictionary from response
            start_idx = content.find('{')
            end_idx = content.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                raise ValueError("No dictionary found in response")
            
            dict_str = content[start_idx:end_idx]
            result = eval(dict_str)
            
            # Validasi struktur data
            if 'hashtags' not in result:
                raise ValueError("Missing hashtags in response")
            
            # Format hasil untuk frontend
            formatted_hashtags = []
            for tag in result['hashtags']:
                formatted_hashtags.append({
                    'tag': tag['tag'],
                    'count': tag['count'],
                    'trend': tag['trend'],
                    'context': tag.get('context', ''),
                    'audience': tag.get('audience', ''),
                    'engagement_rate': tag.get('engagement_rate', '')
                })
            
            # Tambahkan analisis dan rekomendasi
            return {
                'hashtags': formatted_hashtags,
                'analysis': result.get('analysis', ''),
                'recommendation': result.get('recommendation', ''),
                'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
        except Exception as e:
            logger.error(f"Error parsing AI response for hashtags: {str(e)}")
            # Fallback ke data statis jika parsing gagal
            return get_static_hashtags(platform)
            
    except Exception as e:
        logger.error(f"Error analyzing hashtag trends: {str(e)}")
        return get_static_hashtags(platform)

def get_static_hashtags(platform):
    """Fallback function untuk data hashtag statis"""
    static_hashtags = {
        'tiktok': [
            {'tag': '#fyp', 'count': 1000000, 'trend': 'up'},
            {'tag': '#viral', 'count': 800000, 'trend': 'up'},
            {'tag': '#trending', 'count': 600000, 'trend': 'stable'},
            {'tag': '#foryou', 'count': 500000, 'trend': 'up'},
            {'tag': '#foryoupage', 'count': 400000, 'trend': 'down'}
        ],
        'instagram': [
            {'tag': '#reels', 'count': 2000000, 'trend': 'up'},
            {'tag': '#reelsinstagram', 'count': 1500000, 'trend': 'up'},
            {'tag': '#viralreels', 'count': 1000000, 'trend': 'stable'},
            {'tag': '#reelsviral', 'count': 800000, 'trend': 'up'},
            {'tag': '#reelsindia', 'count': 600000, 'trend': 'down'}
        ],
        'youtube': [
            {'tag': '#shorts', 'count': 3000000, 'trend': 'up'},
            {'tag': '#youtubeshorts', 'count': 2500000, 'trend': 'up'},
            {'tag': '#shortsvideo', 'count': 2000000, 'trend': 'stable'},
            {'tag': '#shortsyoutube', 'count': 1500000, 'trend': 'up'},
            {'tag': '#shortsfeed', 'count': 1000000, 'trend': 'down'}
        ],
        'facebook': [
            {'tag': '#facebookreels', 'count': 2500000, 'trend': 'up'},
            {'tag': '#facebookviral', 'count': 2000000, 'trend': 'up'},
            {'tag': '#facebooktrending', 'count': 1800000, 'trend': 'stable'},
            {'tag': '#facebookpost', 'count': 1500000, 'trend': 'up'},
            {'tag': '#facebookcommunity', 'count': 1200000, 'trend': 'up'}
        ]
    }
    if platform == 'facebook':
        return [
            {
                "tag": "#facebookpost",
                "count": 1500000,
                "trend": "up",
                "context": "Post promosi, update status, konten viral",
                "audience": "Pengguna Facebook aktif, komunitas, pebisnis",
                "engagement_rate": "Tinggi (4-7%)"
            },
            {
                "tag": "#facebookcommunity",
                "count": 1200000,
                "trend": "up",
                "context": "Komunitas, diskusi grup, sharing info",
                "audience": "Anggota grup, komunitas niche",
                "engagement_rate": "Sedang (2-4%)"
            },
            # ... tambahkan data lain sesuai kebutuhan ...
        ]
    # ... existing code for other platforms ...
    # Untuk setiap hashtag, pastikan field context, audience, engagement_rate ada
    hashtags = [
        {**h, 
         "context": h.get("context", "Tidak tersedia"),
         "audience": h.get("audience", "Tidak tersedia"),
         "engagement_rate": h.get("engagement_rate", "Tidak tersedia")
        } for h in static_hashtags.get(platform, [])]
    return {
        'hashtags': hashtags,
        'analysis': 'Using fallback data',
        'recommendation': 'Consider refreshing for real-time data',
        'generated_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

@app.route('/analyze_trends/<platform>')
def analyze_trends(platform):
    """Endpoint untuk analisis trending hashtags"""
    try:
        trends = analyze_hashtag_trends(platform)
        return jsonify({
            'status': 'success',
            'platform': platform,
            'data': trends
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def get_best_posting_time(platform, content_type):
    """Analisis waktu posting terbaik berdasarkan platform dan jenis konten"""
    try:
        # Simulasi data waktu posting terbaik (dalam implementasi nyata, ini akan menggunakan data historis)
        best_times = {
            'tiktok': {
                'general': ['18:00', '20:00', '22:00'],
                'entertainment': ['19:00', '21:00', '23:00'],
                'educational': ['09:00', '15:00', '20:00']
            },
            'instagram': {
                'general': ['12:00', '15:00', '18:00'],
                'entertainment': ['13:00', '16:00', '19:00'],
                'educational': ['10:00', '14:00', '17:00']
            },
            'youtube': {
                'general': ['15:00', '18:00', '20:00'],
                'entertainment': ['16:00', '19:00', '21:00'],
                'educational': ['11:00', '15:00', '18:00']
            },
            'facebook': {
                'general': ['09:00', '15:00', '19:00'],
                'entertainment': ['10:00', '16:00', '20:00'],
                'educational': ['08:00', '14:00', '18:00'],
                'business': ['08:00', '12:00', '17:00']
            }
        }
        return best_times.get(platform, {}).get(content_type, ['12:00', '18:00', '20:00'])
    except Exception as e:
        logger.error(f"Error getting best posting time: {str(e)}")
        return ['12:00', '18:00', '20:00']

@app.route('/best_posting_time/<platform>/<content_type>')
def get_posting_time(platform, content_type):
    """Endpoint untuk mendapatkan waktu posting terbaik"""
    try:
        best_times = get_best_posting_time(platform, content_type)
        return jsonify({
            'status': 'success',
            'platform': platform,
            'content_type': content_type,
            'best_times': best_times
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

def analyze_engagement_rate(caption_data):
    """Analisis engagement rate berdasarkan data caption"""
    try:
        # Simulasi perhitungan engagement rate (dalam implementasi nyata, ini akan menggunakan data aktual)
        platform = caption_data.get('platform', 'tiktok')
        
        # Faktor pengali berdasarkan platform
        platform_multipliers = {
            'tiktok': {'likes': 100, 'comments': 10, 'shares': 5},
            'instagram': {'likes': 80, 'comments': 15, 'shares': 8},
            'youtube': {'likes': 120, 'comments': 20, 'shares': 10},
            'facebook': {'likes': 150, 'comments': 25, 'shares': 15}
        }
        
        multipliers = platform_multipliers.get(platform, platform_multipliers['tiktok'])
        
        engagement_metrics = {
            'likes': len(caption_data.get('hashtags', '').split()) * multipliers['likes'],
            'comments': len(caption_data.get('caption', '').split()) * multipliers['comments'],
            'shares': len(caption_data.get('hook', '').split()) * multipliers['shares']
        }
        
        total_engagement = sum(engagement_metrics.values())
        return {
            'metrics': engagement_metrics,
            'total': total_engagement,
            'predicted_reach': total_engagement * (15 if platform == 'facebook' else 10)
        }
    except Exception as e:
        logger.error(f"Error analyzing engagement rate: {str(e)}")
        return {'error': str(e)}

def optimize_caption(caption_data, platform):
    """Optimasi caption berdasarkan performa sebelumnya"""
    try:
        # Analisis performa caption sebelumnya
        similar_captions = [c for c in performance_data[platform] 
                          if any(tag in c.get('hashtags', '') for tag in caption_data.get('hashtags', '').split())]
        
        if similar_captions:
            # Analisis elemen yang berhasil
            successful_hooks = [c.get('hook') for c in similar_captions if c.get('performance', 0) > 0.7]
            successful_ctas = [c.get('cta') for c in similar_captions if c.get('performance', 0) > 0.7]
            
            # Optimasi caption
            if successful_hooks:
                caption_data['hook'] = max(set(successful_hooks), key=successful_hooks.count)
            if successful_ctas:
                caption_data['cta'] = max(set(successful_ctas), key=successful_ctas.count)
            
            # Tambahkan trending hashtags
            trending_tags = analyze_hashtag_trends(platform)
            if trending_tags:
                current_tags = set(caption_data.get('hashtags', '').split())
                new_tags = [tag['tag'] for tag in trending_tags[:2] if tag['tag'] not in current_tags]
                if new_tags:
                    caption_data['hashtags'] = ' '.join(list(current_tags) + new_tags)
        
        return caption_data
    except Exception as e:
        logger.error(f"Error optimizing caption: {str(e)}")
        return caption_data

def ab_test_caption(caption_data, platform):
    """Membuat variasi caption untuk A/B testing"""
    try:
        variations = []
        
        # Variasi 1: Original
        variations.append(caption_data)
        
        # Variasi 2: Optimized
        optimized = optimize_caption(caption_data.copy(), platform)
        variations.append(optimized)
        
        # Variasi 3: Alternative hook
        alt_hook = caption_data.copy()
        alt_hook['hook'] = f"🔥 {alt_hook['hook']}"
        variations.append(alt_hook)
        
        # Variasi 4: Alternative CTA
        alt_cta = caption_data.copy()
        alt_cta['cta'] = f"👉 {alt_cta['cta']}"
        variations.append(alt_cta)
        
        return variations
    except Exception as e:
        logger.error(f"Error creating A/B test variations: {str(e)}")
        return [caption_data]

@app.route('/analyze_engagement', methods=['POST'])
def analyze_engagement():
    """Endpoint untuk analisis engagement rate"""
    try:
        data = request.get_json()
        engagement_data = analyze_engagement_rate(data)
        return jsonify({
            'status': 'success',
            'engagement_data': engagement_data
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/optimize_caption', methods=['POST'])
def optimize_caption_endpoint():
    """Endpoint untuk optimasi caption"""
    try:
        data = request.get_json()
        platform = data.get('platform', 'tiktok')
        optimized = optimize_caption(data, platform)
        return jsonify({
            'status': 'success',
            'optimized_caption': optimized
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/ab_test', methods=['POST'])
def ab_test_endpoint():
    """Endpoint untuk A/B testing"""
    try:
        data = request.get_json()
        platform = data.get('platform', 'tiktok')
        variations = ab_test_caption(data, platform)
        return jsonify({
            'status': 'success',
            'variations': variations
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/logo/<path:filename>')
def logo_static(filename):
    return send_from_directory('logo', filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)