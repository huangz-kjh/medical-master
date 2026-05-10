"""
医学影像预测模块 - 提供预测页面和图像分析功能

此模块负责:
1. 渲染预测页面
2. 处理医学影像文件上传
3. 执行医学影像分析
4. 生成和显示切片
5. 管理预测会话
"""

import os
import random
import io
import torch
import nibabel
import SimpleITK as sitk
import numpy as np
from matplotlib import pyplot as plt
from pyecharts.charts import Bar
import base64
from flask import request, session, jsonify, render_template, make_response, current_app
import subprocess
import shutil
import logging
import traceback
from werkzeug.utils import secure_filename
from datetime import datetime
import time
from scipy import ndimage

# 导入 RAGFlow 聊天函数，用于生成医疗报告
from router.ragflow_chat import chat_with_ragflow

# 配置参数
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "predict", "nnunet_uploaded")
OUTPUT_DIR = os.path.join(BASE_DIR, "predict", "nnunet_output")
MODEL_PATH = os.path.join(BASE_DIR, "predict", "myModel_109.pth")
NII_DEMO_PATH = os.path.join(BASE_DIR, "predict", "demodata", "demo.nii")

# nnUNet模型路径配置
NNUNET_MODEL_BASE = "/root/autodl-tmp/nnunet/nnUNet_results/nnUNet/3d_fullres"
TASK_MODELS = {
    "1": "Task001_BrainTumour",  # 大脑
    "3": "Task003_Liver",  # 肝脏
    "4": "Task004_Hippocampus",  # 海马体
    "6": "Task006_Lung",  # 肺脏
    "7": "Task007_Pancreas",  # 胰腺
    "10": "Task010_Colon",  # 肠道
    "40": "Task040_KiTS"  # 肾脏
}

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

print(f"BASE_DIR: {BASE_DIR}")
print(f"UPLOAD_DIR: {UPLOAD_DIR}")
print(f"OUTPUT_DIR: {OUTPUT_DIR}")

logger = logging.getLogger(__name__)

def calculate_volume(mask_path):
    """计算分割区域的体积"""
    mask_image = sitk.ReadImage(mask_path)
    size = mask_image.GetSize()
    origin = mask_image.GetOrigin()
    spacing = mask_image.GetSpacing()
    mask_array = sitk.GetArrayFromImage(mask_image)
    non_zero_voxels = (mask_array > 0).sum()
    voxel_volume_mm3 = spacing[0] * spacing[1] * spacing[2]
    volume_mm3 = non_zero_voxels * voxel_volume_mm3
    return volume_mm3

def convert_to_nii_gz(nii_path):
    """将.nii文件转换为.nii.gz格式"""
    try:
        img = nibabel.load(nii_path)
        nii_gz_path = nii_path + '.gz'
        nibabel.save(img, nii_gz_path)
        return nii_gz_path, None
    except Exception as e:
        return None, str(e)

def adjust_window(image, window_center, window_width):
    """调整CT窗口"""
    image_min = window_center - window_width / 2.0
    image_max = window_center + window_width / 2.0
    adjusted_image = np.clip(image, image_min, image_max)
    adjusted_image = (adjusted_image - image_min) / (image_max - image_min)
    return adjusted_image

def is_black_mask(mask_array):
    """检查mask是否全黑"""
    return np.all(mask_array == 0)

def convert_3d_to_2d(image_path, mask_path, window_center=30, window_width=400):
    """将3D NIfTI图像转换为2D PNG切片并保存到用户数据库目录"""
    try:
        print(f"开始加载NIfTI图像: {image_path}")
        image = sitk.ReadImage(image_path)
        image_array = sitk.GetArrayFromImage(image)
        print(f"图像加载成功，形状: {image_array.shape}")

        mask = sitk.ReadImage(mask_path)
        mask_array = sitk.GetArrayFromImage(mask)
        print(f"Mask加载成功，形状: {mask_array.shape}")

        user_id = str(session.get('user_id', 'default_user'))
        print(f"用户ID: {user_id} (类型: {type(user_id)})")

        user_db_dir = os.path.abspath(os.path.join(OUTPUT_DIR, user_id, '2D_slices'))
        os.makedirs(user_db_dir, exist_ok=True)
        print(f"创建输出目录: {user_db_dir}")

        if not os.path.exists(user_db_dir):
            raise Exception(f"无法创建输出目录: {user_db_dir}")

        base_name = os.path.basename(image_path)
        file_name = os.path.splitext(base_name)[0]
        if file_name.endswith('.nii'):
            file_name = os.path.splitext(file_name)[0]
        print(f"处理文件名: {file_name}")

        saved_slices = []

        for dim in range(3):
            print(f"\n处理维度 {dim} 的切片...")

            slice_non_zero_ratio = []
            for i in range(mask_array.shape[dim]):
                if dim == 0:
                    mask_slice = mask_array[i, :, :]
                elif dim == 1:
                    mask_slice = mask_array[:, i, :]
                else:  # dim == 2
                    mask_slice = mask_array[:, :, i]

                non_zero_ratio = np.count_nonzero(mask_slice) / mask_slice.size
                slice_non_zero_ratio.append((i, non_zero_ratio))

            slice_non_zero_ratio.sort(key=lambda x: x[1], reverse=True)
            threshold = max(10, sum(1 for _, ratio in slice_non_zero_ratio if ratio > 0.1))
            meaningful_slices = slice_non_zero_ratio[:threshold]
            meaningful_slices.sort(key=lambda x: x[0])
            meaningful_indices = [i for i, _ in meaningful_slices]

            print(f"维度 {dim} 原始切片数量: {mask_array.shape[dim]}, 筛选后有意义的切片数量: {len(meaningful_indices)}")

            for i in meaningful_indices:
                if dim == 0:
                    slice_data = image_array[i, :, :]
                    mask_slice = mask_array[i, :, :]
                elif dim == 1:
                    slice_data = image_array[:, i, :]
                    mask_slice = mask_array[:, i, :]
                else:  # dim == 2
                    slice_data = image_array[:, :, i]
                    mask_slice = mask_array[:, :, i]

                adjusted_slice = adjust_window(slice_data, window_center, window_width)

                image_png_path = os.path.join(user_db_dir, f"{file_name}_dim{dim}_image_{i}.png")
                plt.imsave(image_png_path, adjusted_slice, cmap='gray')

                mask_png_path = os.path.join(user_db_dir, f"{file_name}_dim{dim}_mask_{i}.png")
                plt.imsave(mask_png_path, mask_slice, cmap='gray')

                saved_slices.append((image_png_path, mask_png_path, i, dim))
                print(f"保存维度 {dim} 的切片 {i + 1}/{mask_array.shape[dim]}: {image_png_path} 和 {mask_png_path}")

                if not os.path.exists(image_png_path) or not os.path.exists(mask_png_path):
                    raise Exception(f"切片保存失败: {image_png_path} 或 {mask_png_path}")

        print(f"所有维度的有意义的切片已保存到: {user_db_dir}")
        return True, saved_slices
    except Exception as e:
        print(f"3D转2D转换失败，详细错误: {str(e)}")
        print(f"错误堆栈: {traceback.format_exc()}")
        return False, str(e)

def run_nnunet(input_path, task_id, max_retries=2):
    """运行 nnUNet 预测"""
    retry_count = 0
    last_error = None

    while retry_count <= max_retries:
        try:
            if retry_count > 0:
                logger.info(f"第 {retry_count} 次重试 nnUNet 分析...")

            print(f"开始处理输入文件: {input_path}, 任务ID: {task_id}")

            if not os.path.exists(input_path):
                return None, f"输入文件不存在: {input_path}"

            file_size = os.path.getsize(input_path)
            file_size_mb = file_size / (1024 * 1024)
            logger.info(f"输入文件大小: {file_size_mb:.2f} MB")

            timeout = 300 + (file_size_mb * 30)
            logger.info(f"设置处理超时时间: {timeout/60:.1f} 分钟")

            try:
                with open(input_path, 'rb') as f:
                    f.read(1024)
            except Exception as e:
                return None, f"无法读取输入文件: {str(e)}"

            if input_path.endswith('.nii'):
                print("检测到 .nii 文件，开始转换为 .nii.gz 格式")
                input_path, error = convert_to_nii_gz(input_path)
                if error:
                    return None, f"文件格式转换失败: {error}"
                print(f"转换完成，新文件路径: {input_path}")

            temp_dir_name = f"temp_input_{int(time.time())}_{random.randint(1000, 9999)}"
            temp_input_dir = os.path.join(OUTPUT_DIR, temp_dir_name)
            os.makedirs(temp_input_dir, exist_ok=True)
            print(f"创建临时输入目录: {temp_input_dir}")

            temp_input_path = os.path.join(temp_input_dir, os.path.basename(input_path))
            shutil.copy2(input_path, temp_input_path)
            print(f"复制文件到临时目录: {temp_input_path}")

            output_dir_name = f"nnUNet_output_{int(time.time())}_{random.randint(1000, 9999)}"
            output_dir = os.path.join(OUTPUT_DIR, output_dir_name)
            os.makedirs(output_dir, exist_ok=True)
            print(f"创建输出目录: {output_dir}")

            task_name = TASK_MODELS.get(task_id)
            if not task_name:
                return None, f"不支持的任务ID: {task_id}"

            model_path = os.path.join(NNUNET_MODEL_BASE, task_name, "nnUNetTrainerV2__nnUNetPlansv2.1")

            # 设置nnUNet环境变量
            nnunet_env = os.environ.copy()
            nnunet_env["nnUNet_raw_data_base"] = "/root/autodl-tmp/nnunet/nnUNet_raw_data_base"
            nnunet_env["nnUNet_preprocessed"] = "/root/autodl-tmp/nnunet/nnUNet_preprocessed"
            nnunet_env["RESULTS_FOLDER"] = "/root/autodl-tmp/nnunet/nnUNet_results"

            cmd = f"nnUNet_predict -i {temp_input_dir} -o {output_dir} -t {task_id} -f 4 -m 3d_fullres -tr nnUNetTrainerV2 -p nnUNetPlansv2.1"
            print(f"执行命令: {cmd}")

            process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                env=nnunet_env
            )

            try:
                stdout, stderr = process.communicate(timeout=timeout)
                returncode = process.returncode
            except subprocess.TimeoutExpired:
                process.kill()
                stdout, stderr = process.communicate()
                logger.error(f"nnUNet 执行超时({timeout/60:.1f}分钟)")
                return None, f"分析超时，处理时间过长（已等待{timeout/60:.1f}分钟）。请尝试使用较小的图像文件或联系管理员增加处理时间限制。"

            print(f"命令执行完成，返回码: {returncode}")
            if returncode != 0:
                logger.error(f"命令返回非零状态: {returncode}")
                logger.error(f"错误输出: {stderr}")
                raise Exception(f"nnUNet 执行失败，返回码: {returncode}, 错误: {stderr}")

            if not os.path.exists(output_dir):
                raise Exception(f"输出目录未创建: {output_dir}")

            output_files = [f for f in os.listdir(output_dir) if f.endswith('.nii.gz')]
            print(f"找到的输出文件: {output_files}")

            if not output_files:
                raise Exception(f"未找到 nnUNet 输出文件，目录内容: {os.listdir(output_dir)}")

            output_path = os.path.join(output_dir, output_files[-1])
            print(f"最终输出文件路径: {output_path}")

            try:
                img = nibabel.load(output_path)
                shape = img.shape
                logger.info(f"成功加载输出文件，形状: {shape}")

                if any(dim < 10 for dim in shape):
                    raise Exception(f"输出文件疑似无效，形状异常: {shape}")
            except Exception as e:
                logger.error(f"输出文件验证失败: {str(e)}")
                raise Exception(f"生成的分析结果无效: {str(e)}")

            try:
                shutil.rmtree(temp_input_dir)
                print(f"清理临时目录: {temp_input_dir}")
            except Exception as e:
                print(f"清理临时目录失败: {str(e)}")

            return output_path, None

        except Exception as e:
            logger.error(f"nnUNet 执行失败 (尝试 {retry_count+1}/{max_retries+1}): {str(e)}")
            last_error = str(e)

            try:
                if 'temp_input_dir' in locals() and os.path.exists(temp_input_dir):
                    shutil.rmtree(temp_input_dir)
                if 'output_dir' in locals() and os.path.exists(output_dir):
                    shutil.rmtree(output_dir)
            except Exception as cleanup_error:
                logger.error(f"清理临时目录失败: {str(cleanup_error)}")

            retry_count += 1

            if retry_count <= max_retries:
                wait_time = retry_count * 3
                logger.info(f"等待 {wait_time} 秒后重试...")
                time.sleep(wait_time)
            else:
                return None, f"经过 {max_retries+1} 次尝试后预测失败: {last_error}"

    return None, f"预测过程中出错，所有重试均失败"

def process(nii_path, mask_path, organ_name=None):
    """读取 NIfTI 图像、预处理并调用模型预测，然后构建图表和文字描述"""
    try:
        img = nibabel.load(nii_path).get_fdata()
        img_shape = img.shape

        volume = None
        if mask_path and os.path.exists(mask_path):
            volume = calculate_volume(mask_path)

            print(f"开始将3D图像转换为2D切片，输入文件: {mask_path}")
            success, result = convert_3d_to_2d(nii_path, mask_path)
            if not success:
                print(f"3D转2D转换失败: {result}")
            else:
                print(f"成功保存2D切片到用户数据库，共{len(result)}张切片")
                print(f"切片保存路径: {result[0][0]}")

        result_text = "诊断结果："
        if volume:
            result_text += f" 肿瘤体积: {volume:.2f} mm³,"
        result_text += f" 影像尺寸: {img_shape}"

        if not organ_name:
            if "brain" in nii_path.lower():
                organ_name = "脑部"
            elif "lung" in nii_path.lower():
                organ_name = "肺部"
            elif "liver" in nii_path.lower():
                organ_name = "肝脏"
            elif "kidney" in nii_path.lower():
                organ_name = "肾脏"
            elif "heart" in nii_path.lower():
                organ_name = "心脏"
            else:
                organ_name = "未知"

        result_text += f", 器官类型: {organ_name}"

        return img_shape, None, result_text, None
    except Exception as e:
        print(f"处理过程中出错: {str(e)}")
        return None, None, None, str(e)

def create_slice_image(nii_path, dim, index):
    """创建指定维度和索引的MRI切片图像，返回base64编码"""
    try:
        img = nibabel.load(nii_path).get_fdata()
        if dim < 0 or dim > img.ndim - 1:
            return None, "无效的维度"
        if index < 0 or index >= img.shape[dim]:
            return None, "切片索引超出范围"

        slice_img = img.take(index, axis=dim)

        fig, ax = plt.subplots()
        ax.imshow(slice_img, cmap="gray")
        ax.axis("off")
        buf = io.BytesIO()
        plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
        plt.close(fig)
        buf.seek(0)
        base64_img = base64.b64encode(buf.read()).decode("utf-8")
        return base64_img, None
    except Exception as e:
        return None, str(e)

def init_predict_routes(app):
    @app.route('/predict', methods=["GET"])
    @app.route('/doctor/predict', methods=["GET"])
    def doctor_predict():
        try:
            is_embed = request.args.get('embed', '0') == '1'
            patient_id = request.args.get('patient_id')

            if patient_id:
                # 不再将 patient_id 存储在 session 中，以避免多页面混淆
                logger.info(f"诊断页面加载，关联到患者ID: {patient_id}")

            return render_template("doctor/predict.html", is_embed=is_embed, patient_id=patient_id)
        except Exception as e:
            logger.error(f"加载predict页面失败: {str(e)}")
            return f"<h1>错误</h1><p>加载预测页面时出错: {str(e)}</p>", 500

    @app.route('/predict', methods=["POST"])
    def predict():
        try:
            logger.info("收到文件上传请求")
            content_length = request.content_length
            logger.info(f"请求内容大小: {content_length/1024/1024:.2f} MB")

            if 'file' not in request.files:
                logger.warning("未找到文件")
                return jsonify({"error": "未上传文件"}), 400

            file = request.files['file']
            if not file.filename.endswith(('.nii', '.nii.gz')):
                logger.warning(f"不支持的文件格式: {file.filename}")
                return jsonify({"error": "请上传 .nii 或 .nii.gz 格式的文件"}), 400

            if file.filename == '':
                logger.warning("文件名为空")
                return jsonify({"error": "未选择文件"}), 400

            space_ok, space_err = check_disk_space()
            if not space_ok:
                logger.error(f"磁盘空间检查失败: {space_err}")
                return jsonify({"error": f"服务器存储空间不足: {space_err}"}), 500

            try:
                nii_path = save_uploaded_file(file)
                logger.info(f"保存路径: {nii_path}")
                os.makedirs(UPLOAD_DIR, exist_ok=True)
                session["nii_path"] = nii_path
            except Exception as e:
                logger.error(f"文件保存失败: {str(e)}", exc_info=True)
                return jsonify({"error": f"文件保存失败: {str(e)}"}), 500

            task_id = request.form.get('task_id', '1')
            organ_info = {
                "1": {"name": "大脑", "normal_volume": "1200-1500 cm³"},
                "3": {"name": "肝脏", "normal_volume": "1200-1500 cm³"},
                "4": {"name": "海马体", "normal_volume": "3-4 cm³"},
                "6": {"name": "肺脏", "normal_volume": "4000-6000 cm³"},
                "7": {"name": "胰腺", "normal_volume": "70-100 cm³"},
                "10": {"name": "肠道", "normal_volume": "1000-1500 cm³"},
                "40": {"name": "肾脏", "normal_volume": "120-150 cm³"}
            }

            try:
                output_path, error = run_nnunet(nii_path, task_id)
                if error:
                    logger.error(f"nnUNet预测失败: {error}")
                    return jsonify({"error": error}), 500
            except Exception as e:
                logger.error(f"nnUNet预测过程异常: {str(e)}", exc_info=True)
                return jsonify({"error": f"分析过程异常: {str(e)}"}), 500

            session["output_path"] = output_path
            current_organ_name = organ_info[task_id]["name"]

            volume = None
            if output_path and os.path.exists(output_path):
                try:
                    volume = calculate_volume(output_path)
                except Exception as e:
                    logger.error(f"体积计算失败: {str(e)}")
                    volume = None

            result_text = "诊断结果："
            if volume:
                result_text += f" 肿瘤体积: {volume:.2f} mm³,"
            result_text += f" 器官类型: {current_organ_name}"

            # 从请求的表单数据中直接获取患者ID，不再依赖session
            patient_id = request.form.get("patient_id")

            imaging_id = None
            if patient_id:
                logger.info(f"本次预测明确关联到患者ID: {patient_id} (来自表单)")
                try:
                    # 导入数据库模型
                    from db_model import db, MedicalImaging

                    # 创建预测记录
                    new_imaging = MedicalImaging(
                        patient_id=patient_id,
                        doctor_id=session.get('user_id'),
                        image_type=current_organ_name,
                        file_path=nii_path,
                        result_path=output_path if output_path else "",
                        result_text=result_text,
                        tumor_volume=volume if volume else 0,
                        created_at=datetime.now()
                    )

                    # 保存到数据库
                    db.session.add(new_imaging)
                    db.session.commit()

                    # 获取新记录的ID，用于后续报告关联
                    imaging_id = new_imaging.imaging_id
                    session['imaging_id'] = imaging_id  # 保存到会话中，供 generate_report 使用
                    logger.info(f"已保存预测结果到数据库，患者ID: {patient_id}, 影像记录ID: {imaging_id}")

                    # 在响应中添加患者关联信息
                    result_text += f"（已关联到患者ID: {patient_id}）"
                except Exception as e:
                    logger.error(f"保存预测结果到患者记录失败: {str(e)}", exc_info=True)
                    db.session.rollback()  # 发生错误时回滚

            response = {
                "success": True,
                "result": result_text,
                "organ": current_organ_name,
                "normal_volume": organ_info[task_id]["normal_volume"],
                "imaging_id": imaging_id  # 将新的影像记录ID返回给前端
            }

            try:
                if output_path and os.path.exists(output_path):
                    success, slices_result = convert_3d_to_2d(nii_path, output_path)
                    if success:
                        response["total_slices"] = len(slices_result)
                        preview_slices = []
                        for dim in range(3):
                            dim_slices = [s for s in slices_result if s[3] == dim][:3]
                            for slice_info in dim_slices:
                                try:
                                    with open(slice_info[0], 'rb') as f:
                                        img_data = base64.b64encode(f.read()).decode('utf-8')
                                        preview_slices.append({
                                            'dim': dim,
                                            'index': slice_info[2],
                                            'img': img_data
                                        })
                                except Exception as e:
                                    logger.error(f"读取预览切片失败: {str(e)}")
                                    continue
                        response["preview_slices"] = preview_slices
            except Exception as e:
                logger.error(f"3D转2D转换失败: {str(e)}")
                pass

            return jsonify(response)

        except Exception as e:
            logger.error(f"文件处理失败: {str(e)}")
            logger.error(traceback.format_exc())

            error_message = str(e)
            if "413" in error_message or "RequestEntityTooLarge" in error_message:
                return jsonify({"error": "文件太大，请尝试压缩或分割文件后再上传"}), 413

            return jsonify({"error": f"文件处理失败: {str(e)}"}), 500

    @app.route('/predict_demo', methods=["POST"])
    def predict_demo():
        try:
            nii_path = NII_DEMO_PATH
            if not os.path.exists(nii_path):
                return jsonify({"error": "示例图像文件不存在"}), 404

            session["nii_path"] = nii_path

            demo_organ = "大脑"
            img_shape, chart_html, result_text, error = process(nii_path, None, demo_organ)

            if error:
                return jsonify({"error": error}), 500

            return jsonify({
                "chart": chart_html,
                "result": result_text,
                "img_shape": img_shape,
                "organ": demo_organ,
                "normal_volume": "1200-1500 cm³"
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/view_slice', methods=['GET'])
    def view_slice():
        try:
            dim = int(request.args.get("dim", 0))
            index = int(request.args.get("index", 0))

            if dim not in [0, 1, 2]:
                return jsonify({"error": "无效的维度参数"}), 400

            nii_path = session.get("nii_path")
            output_path = session.get("output_path")

            logger.info(f"原始图像路径: {nii_path}")
            logger.info(f"分割结果路径: {output_path}")

            if not nii_path or not os.path.exists(nii_path):
                if os.path.exists(NII_DEMO_PATH):
                    logger.info(f"使用示例图像生成切片")
                    nii_path = NII_DEMO_PATH
                else:
                    return jsonify({"error": "未找到可用的图像文件，请先上传或使用示例"}), 400

            try:
                img = nibabel.load(nii_path).get_fdata()
                logger.info(f"原始图像形状: {img.shape}")
            except Exception as e:
                logger.error(f"加载原始图像失败: {str(e)}")
                return jsonify({"error": f"加载图像失败: {str(e)}"}), 500

            if index < 0 or index >= img.shape[dim]:
                return jsonify({"error": "切片索引超出范围"}), 400

            if dim == 0:
                slice_img = img[index, :, :]
            elif dim == 1:
                slice_img = img[:, index, :]
            else:  # dim == 2
                slice_img = img[:, :, index]

            adjusted_slice = adjust_window(slice_img, window_center=30, window_width=400)
            rgb_slice = np.stack([adjusted_slice] * 3, axis=-1)

            if output_path and os.path.exists(output_path):
                try:
                    mask = nibabel.load(output_path).get_fdata()
                    logger.info(f"分割结果形状: {mask.shape}")

                    if dim == 0:
                        mask_slice = mask[index, :, :]
                    elif dim == 1:
                        mask_slice = mask[:, index, :]
                    else:  # dim == 2
                        mask_slice = mask[:, :, index]

                    mask_slice = (mask_slice > 0.5).astype(np.uint8)
                    edges = ndimage.binary_dilation(mask_slice) - mask_slice
                    rgb_slice[edges > 0] = [1, 0, 0]  # 红色

                except Exception as e:
                    logger.error(f"添加分割轮廓时出错: {str(e)}")
                    logger.error(traceback.format_exc())

            fig, ax = plt.subplots()
            ax.imshow(rgb_slice)
            ax.axis("off")
            buf = io.BytesIO()
            plt.savefig(buf, format="png", bbox_inches="tight", pad_inches=0)
            plt.close(fig)
            buf.seek(0)
            base64_img = base64.b64encode(buf.read()).decode("utf-8")

            return jsonify({"slice_img": base64_img})
        except Exception as e:
            logger.error(f"查看切片出错: {str(e)}")
            logger.error(traceback.format_exc())
            return jsonify({"error": str(e)}), 500

    @app.route('/save_slice', methods=['POST'])
    def save_slice():
        try:
            data = request.get_json()
            img_data = data.get('img')
            dim = data.get('dim')
            index = data.get('index')
            diagnosis_info = data.get('diagnosis_info')  # 新增：获取诊断信息

            if not img_data:
                return jsonify({'error': '没有图像数据'}), 400

            if "," in img_data:
                img_data = img_data.split(",")[1]

            # 创建基础下载目录
            base_save_dir = os.path.join('predict', 'download_img')
            os.makedirs(base_save_dir, exist_ok=True)

            # 获取或创建会话ID
            session_id = session.get('slice_session_id')
            if not session_id:
                session_id = f"session_{int(time.time())}_{random.randint(1000, 9999)}"
                session['slice_session_id'] = session_id

            # 创建会话特定的目录
            session_dir = os.path.join(base_save_dir, session_id)
            os.makedirs(session_dir, exist_ok=True)

            # 如果是第一次保存，创建诊断信息文件
            if not os.path.exists(os.path.join(session_dir, 'diagnosis_info.txt')):
                with open(os.path.join(session_dir, 'diagnosis_info.txt'), 'w', encoding='utf-8') as f:
                    f.write(diagnosis_info)

            # 保存切片图片
            timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
            filename = f'slice_dim{dim}_index{index}_{timestamp}.png'
            save_path = os.path.join(session_dir, filename)

            with open(save_path, 'wb') as f:
                f.write(base64.b64decode(img_data))

            # 获取当前会话中所有已保存的切片
            saved_slices = []
            for f in sorted(os.listdir(session_dir)):
                if f.endswith('.png'):
                    with open(os.path.join(session_dir, f), 'rb') as img_file:
                        img_data = base64.b64encode(img_file.read()).decode('utf-8')
                        saved_slices.append({
                            'filename': f,
                            'img': img_data
                        })

            return jsonify({
                'message': '保存成功',
                'filename': filename,
                'session_id': session_id,
                'saved_slices': saved_slices
            })

        except Exception as e:
            logger.error(f"保存切片时出错: {str(e)}")
            return jsonify({'error': str(e)}), 500

    @app.route('/generate_report', methods=['POST'])
    def generate_report():
        try:
            data = request.get_json()
            diagnosis_info = data.get('diagnosis_info')
            imaging_id = data.get('imaging_id') or session.get('imaging_id')

            if not diagnosis_info:
                return jsonify({'error': '诊断信息缺失'}), 400

            # 默认值
            organ_name = "未知器官"
            volume_mm3 = 0
            patient_id = None

            # 如果有imaging_id，从数据库获取更精确的信息
            if imaging_id:
                from db_model import MedicalImaging
                imaging_record = MedicalImaging.query.get(imaging_id)
                if imaging_record:
                    organ_name = imaging_record.image_type
                    volume_mm3 = imaging_record.tumor_volume or 0
                    patient_id = imaging_record.patient_id
                    logger.info(f"从影像记录(ID:{imaging_id})加载数据: 器官={organ_name}, 体积={volume_mm3}, 患者ID={patient_id}")

            # 构建prompt
            prompt = f"""
            请根据以下信息，为患者生成一份专业的医疗影像报告摘要。

            患者影像分析结果：
            - 诊断信息: {diagnosis_info}
            - 分析器官：{organ_name}
            - 病灶体积：{volume_mm3:.2f} mm³

            请直接生成一段通顺的报告解读文本，总结以上信息，并给出可能的建议。
            """

            # 记录发送给RAGFlow的最终提示
            user_id = session.get('user_id', 'default_user')
            logger.info(f"发送给RAGFlow的Prompt: {prompt}")

            conclusion_response = chat_with_ragflow(prompt, user_id, stream=False, use_file_chat=False)

            if not conclusion_response or 'response' not in conclusion_response:
                raise Exception("RAGFlow服务未返回有效结论。")

            conclusion = conclusion_response['response']

            # 如果有关联的患者和影像记录，保存报告到数据库
            if patient_id and imaging_id:
                try:
                    from db_model import db, ImagingReport
                    from datetime import date

                    # 创建成像报告记录
                    new_report = ImagingReport(
                        patient_id=patient_id,
                        imaging_id=imaging_id,
                        report_type=f"AI辅助诊断-{organ_name}",
                        report_date=date.today(),
                        analysis_result=diagnosis_info,
                        conclusion=conclusion,
                        created_at=datetime.now()
                    )

                    db.session.add(new_report)
                    db.session.commit()
                    logger.info(f"已保存诊断报告到患者ID: {patient_id}, 关联影像ID: {imaging_id}")
                    conclusion += f"\\n\\n[系统信息: 此报告已保存到患者(ID: {patient_id})的医疗记录]"
                except Exception as e:
                    logger.error(f"保存报告到患者记录失败: {str(e)}", exc_info=True)
                    db.session.rollback()

            return jsonify({
                'report': conclusion,
                'patient_id': patient_id,
                'saved': bool(patient_id and imaging_id)
            })

        except Exception as e:
            logger.error(f"生成报告失败: {str(e)}")
            return jsonify(status="error", message=f"生成报告失败: {str(e)}"), 500

    @app.route('/clear_slice_session', methods=['POST'])
    def clear_slice_session():
        """清除切片会话"""
        try:
            session.pop('slice_session_id', None)
            return jsonify({'message': '会话已清除'})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    @app.route('/view_2d_slices', methods=['GET'])
    def view_2d_slices():
        try:
            user_id = session.get('user_id')
            if not user_id:
                return jsonify({"error": "用户未登录"}), 401

            output_folder = os.path.join(OUTPUT_DIR, str(user_id), "2D_slices")
            if not os.path.exists(output_folder):
                return jsonify({"error": "2D切片文件夹不存在"}), 400

            slices = []
            for filename in sorted(os.listdir(output_folder)):
                if filename.endswith('.png') and 'image' in filename:
                    with open(os.path.join(output_folder, filename), 'rb') as f:
                        img_data = base64.b64encode(f.read()).decode('utf-8')
                        parts = filename.split('_')
                        index = int(parts[-1].split('.')[0])
                        slices.append({
                            'index': index,
                            'img': img_data
                        })

            if not slices:
                return jsonify({"error": "未找到任何切片"}), 404

            slices.sort(key=lambda x: x['index'])

            total_slices = len(slices)
            displayed_slices = len([s for s in slices if s['img']])

            return jsonify({
                'slices': slices,
                'total_slices': total_slices,
                'displayed_slices': displayed_slices
            })
        except Exception as e:
            print(f"查看2D切片时出错: {str(e)}")
            return jsonify({"error": str(e)}), 500

    @app.route('/predict/debug_session', methods=['GET'])
    def debug_predict_session():
        try:
            output_path = session.get("output_path", "未设置")
            nii_path = session.get("nii_path", "未设置")

            output_exists = False
            if output_path != "未设置":
                output_exists = os.path.exists(output_path)

            nii_exists = False
            if nii_path != "未设置":
                nii_exists = os.path.exists(nii_path)

            demo_exists = os.path.exists(NII_DEMO_PATH)

            return jsonify({
                "output_path": output_path,
                "output_exists": output_exists,
                "nii_path": nii_path,
                "nii_exists": nii_exists,
                "demo_path": NII_DEMO_PATH,
                "demo_exists": demo_exists,
                "user_id": session.get("user_id", "未登录"),
                "session_keys": list(session.keys())
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    @app.route('/test/predict', methods=['GET'])
    def test_predict():
        try:
            return jsonify({
                "status": "success",
                "message": "Predict路由工作正常",
                "route": "/predict",
                "methods": ["GET", "POST"],
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            return jsonify({
                "status": "error",
                "message": str(e),
                "route": "/test/predict",
                "timestamp": datetime.now().isoformat()
            }), 500

    @app.before_request
    def check_session():
        logger.info(f"请求: {request.endpoint}, 方法: {request.method}, 路径: {request.path}")

        if request.endpoint == 'doctor_predict' and request.method == "GET":
            return None

        if request.endpoint == 'view_slice' and request.method == 'GET':
            return None

        if request.endpoint in ['predict', 'view_slice', 'save_slice'] and request.method != "GET":
            if not session.get('user_id'):
                logger.warning(f"未授权访问: {request.endpoint}")
                return jsonify({"error": "请先登录"}), 401

    logger.info(f"predict路由注册完成")

def is_normal_volume(volume, task_id):
    """检查器官体积是否在正常范围内"""
    volume_cm3 = volume / 1000.0

    normal_ranges = {
        "1": (1200, 1500),  # 大脑
        "3": (1200, 1500),  # 肝脏
        "4": (3, 4),        # 海马体
        "6": (4000, 6000),  # 肺脏
        "7": (70, 100),     # 胰腺
        "10": (1000, 1500), # 肠道
        "40": (120, 150)    # 肾脏
    }

    if task_id in normal_ranges:
        min_vol, max_vol = normal_ranges[task_id]
        return min_vol <= volume_cm3 <= max_vol

    return True

def predict_with_nnunet(nii_path, task_id):
    try:
        output_path, error = run_nnunet(nii_path, task_id)
        if error:
            return {"error": error}

        volume = calculate_volume(output_path)
        organ_info = {
            "1": {"name": "大脑", "normal_volume": "1200-1500 cm³"},
            "3": {"name": "肝脏", "normal_volume": "1200-1500 cm³"},
            "4": {"name": "海马体", "normal_volume": "3-4 cm³"},
            "6": {"name": "肺脏", "normal_volume": "4000-6000 cm³"},
            "7": {"name": "胰腺", "normal_volume": "70-100 cm³"},
            "10": {"name": "肠道", "normal_volume": "1000-1500 cm³"},
            "40": {"name": "肾脏", "normal_volume": "120-150 cm³"}
        }

        return {
            "organ": organ_info[task_id]["name"],
            "volume": f"{volume:.2f} mm³",
            "normal_range": organ_info[task_id]["normal_volume"],
            "status": "正常" if is_normal_volume(volume, task_id) else "异常"
        }
    except Exception as e:
        return {"error": str(e)}

def save_uploaded_file(file):
    """保存上传的文件并返回文件路径"""
    try:
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        user_id = session.get('user_id', 'anonymous')
        filename = f"{user_id}_{timestamp}_{secure_filename(file.filename)}"
        file_path = os.path.join(UPLOAD_DIR, filename)

        os.makedirs(UPLOAD_DIR, exist_ok=True)

        space_ok, space_error = check_disk_space()
        if not space_ok:
            raise Exception(f"磁盘空间不足: {space_error}")

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        logger.info(f"准备保存文件: {filename}, 大小: {file_size/1024/1024:.2f} MB")

        file.save(file_path)

        if not os.path.exists(file_path):
            raise Exception("文件保存失败: 无法在目标位置找到文件")

        saved_size = os.path.getsize(file_path)
        if saved_size == 0:
            raise Exception("文件保存失败: 文件大小为0")

        logger.info(f"文件成功保存至: {file_path}, 实际保存大小: {saved_size/1024/1024:.2f} MB")
        return file_path

    except Exception as e:
        logger.error(f"文件保存过程中出错: {str(e)}", exc_info=True)
        try:
            if 'file_path' in locals() and os.path.exists(file_path):
                os.remove(file_path)
                logger.info(f"已删除部分保存的文件: {file_path}")
        except:
            pass
        raise Exception(f"文件保存失败: {str(e)}")

def check_disk_space():
    """检查磁盘空间是否充足"""
    try:
        total, used, free = shutil.disk_usage(UPLOAD_DIR)

        if free < 1024 * 1024 * 1024:
            logger.warning(f"磁盘空间不足: 仅剩 {free/1024/1024/1024:.2f} GB")
            return False, f"剩余空间不足1GB，当前可用: {free/1024/1024/1024:.2f} GB"

        usage_percent = (used / total) * 100
        logger.info(f"当前磁盘使用情况: 总容量 {total/1024/1024/1024:.2f} GB, "
                   f"已用 {used/1024/1024/1024:.2f} GB ({usage_percent:.1f}%), "
                   f"可用 {free/1024/1024/1024:.2f} GB")

        return True, None
    except Exception as e:
        logger.error(f"检查磁盘空间时出错: {str(e)}", exc_info=True)
        return False, f"无法检查磁盘空间: {str(e)}"
