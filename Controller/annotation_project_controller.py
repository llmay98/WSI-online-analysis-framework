import time
import os
import numpy
import cv2
import shutil
import uuid
import openslide
from pathlib import Path
from PIL import Image

from Controller.make_archive_threadsafe import make_archive_threadsafe
from Model import manifest
from Controller import manifest_controller
from Model import freehand_annotation_sqlite
from Model import nuclei_annotation_sqlite

manifest_root = "Data/annotation_project_manifest/"
nuclei_annotation_root = "Data/nuclei_annotation_data/"
freehand_annotation_root = "Data/freehand_annotation_data/"
original_data_root = "Data/Original_data/"
export_annotation_root = "static/export/"


def get_table():
    global annotation_project_table
    refresh_nuclei_annotation_export()
    refresh_freehand_annotation_export()
    filename = manifest_root + 'table.npy'
    if not os.path.exists(filename):
        refresh_npy()
    result = annotation_project_table.copy()  # numpy.load(filename)
    result = result.tolist()
    return result


def refresh_nuclei_annotation_progress():
    global annotation_project_table
    filename = manifest_root + 'table.npy'
    if not os.path.exists(filename):
        refresh_npy()
    else:
        result = annotation_project_table.copy()  # numpy.load(filename)
        for i in range(len(result)):
            manifest_txt = open(manifest_root + result[i][0] + '.txt').readlines()
            annotation_project_root = nuclei_annotation_root + result[i][0] + '/'

            annotator_no = 6
            region_no = 0
            finish_region_no = numpy.zeros(annotator_no)
            for wsi in manifest_txt:
                info = wsi.split('\t')
                if not os.path.exists(annotation_project_root + info[0] + '/'):
                    continue
                tba_list_db = annotation_project_root + info[0] + '/' + 'tba_list.db'
                if not os.path.exists(tba_list_db):
                    continue
                db = nuclei_annotation_sqlite.SqliteConnector(tba_list_db)
                tba_result = db.get_RegionID_Centre()
                region_no = region_no + len(tba_result)
                for item in tba_result:
                    for annotator_id in range(annotator_no):
                        if os.path.exists(annotation_project_root + info[0] + '/' +
                                          'a' + str(annotator_id + 1) + '_r' + str(item[0]) + "_annotation.txt") and \
                                sum(numpy.loadtxt(annotation_project_root + info[0] + '/' +
                                                  'a' + str(annotator_id + 1) + '_r' + str(
                                    item[0]) + "_annotation.txt")) > 0:
                            finish_region_no[annotator_id] += 1
            result_str = ""  # 'Total: ' + str(region_no) + ', <br/>'
            for annotator_id in range(annotator_no):
                result_str += str(annotator_id + 1) + ': ' + \
                              str(int(finish_region_no[annotator_id])) + ' /' + str(region_no) + ', '
                if annotator_id % 2:
                    result_str += '<br/>'
            result[i][4] = result_str

        filename = manifest_root + 'table.npy'
        result = numpy.array(result)

        annotation_project_table = result.copy()
        numpy.save(filename, result)  # 保存为.npy格式
    return


def refresh_freehand_annotation_progress():
    global annotation_project_table
    filename = manifest_root + 'table.npy'
    if not os.path.exists(filename):
        refresh_npy()
    else:
        result = annotation_project_table.copy()  # numpy.load(filename)
        for i in range(len(result)):
            manifest_txt = open(manifest_root + result[i][0] + '.txt').readlines()
            annotation_project_root = freehand_annotation_root + result[i][0] + '/'

            annotator_no = 6
            region_no = 0
            finish_region_no = numpy.zeros(annotator_no)
            for wsi in manifest_txt:
                info = wsi.split('\t')
                region_no = region_no + 1
                if not os.path.exists(annotation_project_root + info[0] + '/'):
                    continue
                for annotator_id in range(annotator_no):
                    if os.path.exists(annotation_project_root + info[0] + '/' +
                                      'a' + str(annotator_id + 1) + '.db') and \
                            check_freehand_annotation(annotation_project_root + info[0] + '/' +
                                                      'a' + str(annotator_id + 1) + '.db') > 0:
                        finish_region_no[annotator_id] += 1
            result_str = ""  # 'Total: ' + str(region_no) + ', <br/>'
            for annotator_id in range(annotator_no):
                result_str += str(annotator_id + 1) + ': ' + \
                              str(int(finish_region_no[annotator_id])) + ' /' + str(region_no) + ', '
                if annotator_id % 2:
                    result_str += '<br/>'
            result[i][5] = result_str

        filename = manifest_root + 'table.npy'
        result = numpy.array(result)

        annotation_project_table = result.copy()
        numpy.save(filename, result)  # 保存为.npy格式
    return


def export_freehand_annotation_list(manifest_name):
    manifest_txt = open(export_annotation_root + manifest_name + '_slide_table.txt').readlines()
    annotation_project_root = freehand_annotation_root + manifest_name + '/'
    annotator_no = 6
    result = []
    for wsi in manifest_txt:
        info = wsi.split('\t')
        if not os.path.exists(annotation_project_root + info[1] + '/'):
            continue
        flag = 0
        for annotator_id in range(annotator_no):
            if os.path.exists(annotation_project_root + info[1] + '/' +
                              'a' + str(annotator_id + 1) + '.db') and \
                    check_freehand_annotation(annotation_project_root + info[1] + '/' +
                                                                   'a' + str(
                        annotator_id + 1) + '.db') > 0:
                flag = 1
                wsi += '\t' + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(
                    os.stat(annotation_project_root + info[1] + '/' + 'a' + str(annotator_id + 1) + '.db').st_mtime))
            else:
                wsi += '\t' + "No Annotation"
        if flag == 1:
            temp = {
                "Slide ID": wsi.split("\t")[0],
                "UUID": wsi.split("\t")[1],
                "svs file": wsi.split("\t")[2],
                "a1": wsi.split("\t")[3],
                "a2": wsi.split("\t")[4],
                "a3": wsi.split("\t")[5],
                "a4": wsi.split("\t")[6],
                "a5": wsi.split("\t")[7],
                "a6": wsi.split("\t")[8],
                "Download Link": "<a target='_blank' href='/export_freehand_annotation_single?" \
                                 "manifest_file=Data/annotation_project_manifest/" + manifest_name + \
                                 ".txt&slide_id=" + wsi.split("\t")[1] + "'> Export </a>",

            }
            result.append(temp)
    return result


def export_nuclei_annotation_list(manifest_name):
    manifest_txt = open(export_annotation_root + manifest_name + '_slide_table.txt').readlines()
    annotation_project_root = freehand_annotation_root + manifest_name + '/'
    annotator_no = 6
    result = []
    for wsi in manifest_txt:
        info = wsi.split('\t')
        flag = 0

        nuclei_annotation_root = "Data/nuclei_annotation_data/"
        annotation_project_root = nuclei_annotation_root + manifest_name + '/'
        if not os.path.exists(annotation_project_root + info[1] + '/'):
            continue
        tba_list_db = annotation_project_root + info[1] + '/' + 'tba_list.db'
        if not os.path.exists(tba_list_db):
            continue
        db = nuclei_annotation_sqlite.SqliteConnector(tba_list_db)
        tba_result = db.get_RegionID_Centre()
        if len(tba_result) == 0:
            continue
        for annotator_id in range(annotator_no):
            annotated = 0
            st_time_list = []
            for item in tba_result:
                if os.path.exists(annotation_project_root + info[1] + '/' +
                                  'a' + str(annotator_id) + '_r' + str(item[0]) + "_annotation.txt") and \
                        sum(numpy.loadtxt(annotation_project_root + info[1] + '/' + 'a' + str(annotator_id) +
                                          '_r' + str(item[0]) + "_annotation.txt")) > 0:
                    annotated += 1
                    st_time_list.append(os.stat(annotation_project_root + info[1] + '/' + 'a' + str(annotator_id) +
                                                '_r' + str(item[0]) + "_annotation.txt").st_mtime)
            if len(st_time_list) > 0:
                wsi += time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(max(st_time_list))) \
                       + ' (' + str(annotated) + '/' + str(len(tba_result)) + ') ' + '\t'
                flag = 1
            else:
                wsi += "No Annotation" + '\t'
        if flag:
            temp = {
                "Slide ID": wsi.split("\t")[0],
                "UUID": wsi.split("\t")[1],
                "svs file": wsi.split("\t")[2],
                "a1": wsi.split("\t")[3],
                "a2": wsi.split("\t")[4],
                "a3": wsi.split("\t")[5],
                "a4": wsi.split("\t")[6],
                "a5": wsi.split("\t")[7],
                "a6": wsi.split("\t")[8],
                "Download Link": "<a target='_blank' href='/export_nuclei_annotation_single?" \
                                 "manifest_file=Data/annotation_project_manifest/" + manifest_name + \
                                 ".txt&slide_id=" + wsi.split("\t")[1] + "'> Export </a>",

            }
            result.append(temp)
    return result


def export_region_annotation_list(manifest_name):
    manifest_txt = open(export_annotation_root + manifest_name + '_slide_table.txt').readlines()
    result = []
    for wsi in manifest_txt:
        info = wsi.split('\t')

        nuclei_annotation_root = "Data/nuclei_annotation_data/"
        annotation_project_root = nuclei_annotation_root + manifest_name + '/'
        if not os.path.exists(annotation_project_root + info[1] + '/'):
            continue
        tba_list_db = annotation_project_root + info[1] + '/' + 'tba_list.db'
        if not os.path.exists(tba_list_db):
            continue
        db = nuclei_annotation_sqlite.SqliteConnector(tba_list_db)
        tba_result = db.get_RegionID_Centre()
        if len(tba_result) == 0:
            continue

        wsi += "\t" + str(len(tba_result)) + "\t" + time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(
            os.stat(tba_list_db).st_mtime)) + "\t\t\t\t\t"
        temp = {
            "Slide ID": wsi.split("\t")[0],
            "UUID": wsi.split("\t")[1],
            "svs file": wsi.split("\t")[2],
            "a1": wsi.split("\t")[3],
            "a2": wsi.split("\t")[4],
            "a3": wsi.split("\t")[5],
            "a4": wsi.split("\t")[6],
            "a5": wsi.split("\t")[7],
            "a6": wsi.split("\t")[8],
        }
        result.append(temp)
    return result


def refresh_nuclei_annotation_export():
    global annotation_project_table
    filename = manifest_root + 'table.npy'
    if not os.path.exists(filename):
        refresh_npy()
    else:
        result = annotation_project_table.copy()  # numpy.load(filename)
        file_list = sorted(os.listdir("export"))
        file = '<a >Unavailable</ a>'
        for i in range(len(result)):
            result[i][0]
            file_url = '<a >Unavailable</ a>'
            file = result[i][0] + "_nuclei_annotation.zip?a=" + str(uuid.uuid1())
            if result[i][0] + "_nuclei_annotation.zip" in file_list:
                file_url = '<a href="/static/export/' + file + '">Download</ a>'
            result_str = file_url + ' <br/>' + '<a href= "/export_nuclei_annotation?manifest_file=' + \
                         manifest_root + result[i][0] + '.txt">(re)Export</ a>'
            result_str += '</br> <a href= "/export_nuclei_annotation_page?manifest_file=' + \
                          result[i][0] + '">Anno Table</ a>'
            result_str += '</br> <a href= "/export_region_annotation_page?manifest_file=' + \
                          result[i][0] + '">Region Table</ a>'
            result[i][8] = result_str

        filename = manifest_root + 'table.npy'
        result = numpy.array(result)

        annotation_project_table = result.copy()
        numpy.save(filename, result)  # 保存为.npy格式
    return


def refresh_freehand_annotation_export():
    global annotation_project_table
    filename = manifest_root + 'table.npy'
    if not os.path.exists(filename):
        refresh_npy()
    else:
        result = annotation_project_table.copy()  # numpy.load(filename)
        file_list = sorted(os.listdir("export"))
        file = '<a >Unavailable</ a>'
        for i in range(len(result)):
            result[i][0]
            file_url = '<a >Unavailable</ a>'
            file = result[i][0] + "_freehand_annotation.zip?a=" + str(uuid.uuid1())
            if result[i][0] + "_freehand_annotation.zip" in file_list:
                file_url = '<a href="/static/export/' + file + '">Download</ a>'
            result_str = file_url + ' <br/>' + '<a href= "/export_freehand_annotation?manifest_file=' + \
                         manifest_root + result[i][0] + '.txt">(re)Export</ a>'
            result_str += '</br> <a href= "/export_freehand_annotation_page?manifest_file=' + \
                          result[i][0] + '">Anno Table</ a>'
            result[i][9] = result_str

        filename = manifest_root + 'table.npy'
        result = numpy.array(result)

        annotation_project_table = result.copy()
        numpy.save(filename, result)  # 保存为.npy格式
    return


def export_nuclei_annotation_data(manifest_file_url, manifest_txt=None, export_file=None):
    annotation_project_root = nuclei_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4] + '/'
    if manifest_txt != None:
        export_annotation_root_temp = "static/cache/" + str(uuid.uuid4()) + "/"
        if export_file == None:
            export_file = export_annotation_root_temp.replace("/cache", "")[:-1] + '.zip'
        print(export_file)
        if os.path.exists(export_file):
            os.remove(export_file)

        export_path = export_annotation_root_temp
        if os.path.exists(export_path):
            shutil.rmtree(export_path)
        os.mkdir(export_path)

    else:
        manifest_txt = open(manifest_file_url).readlines()
        if not (not (manifest_file_url.rsplit("/", 1)[1][:-4] == "") and not (
                manifest_file_url.rsplit("/", 1)[1][:-4] is None)):
            return
        export_file = export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4] + '_nuclei_annotation.zip'
        if os.path.exists(export_file):
            os.remove(export_file)

        export_path = export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4] + '/nuclei_annotation/'
        if os.path.exists(export_path):
            shutil.rmtree(export_path)
        elif not os.path.exists(export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4]):
            os.mkdir(export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4])
        os.mkdir(export_path)

    colour = [[255, 0, 209], [0, 255, 255], [0, 0, 255], [0, 0, 255],
              [255, 191, 0], [0, 0, 0], [0, 0, 0]]

    # colour = [tuple([124, 252, 0]), tuple([0, 255, 255]), tuple([137, 43, 224]),
    #           tuple([255 * 0.82, 255 * 0.41, 255 * 0.12]), tuple([255, 0, 0]), tuple([0, 128, 255])]
    # color_scheme = [
    #     [0.49, 0.99, 0], [0, 1, 1], [0.54, 0.17, 0.88], [0.82, 0.41, 0.12],
    #     [1, 0, 0], [0, 0.5, 1]
    # ]

    annotator_no = 6
    for annotator_id in range(annotator_no):
        os.mkdir(export_path + 'a' + str(annotator_id + 1) + '/')
    wsi_count = 0
    for wsi in manifest_txt:
        print(wsi)
        wsi_count += 1
        print(time.asctime(time.localtime(time.time())),
              "start export nuclei annotation:" + str(wsi_count) + '/' + str(len(manifest_txt)))
        info = wsi.split('\t')
        if not os.path.exists(annotation_project_root + info[0] + '/'):
            continue
        tba_list_db = annotation_project_root + info[0] + '/' + 'tba_list.db'
        if not os.path.exists(tba_list_db):
            continue
        db = nuclei_annotation_sqlite.SqliteConnector(tba_list_db)
        tba_result = db.get_RegionID_Centre()
        for item in tba_result:
            original_pic_url = annotation_project_root + info[0] + '/' + 'r' + str(item[0]) + '.png'
            original_pic = cv2.imread(original_pic_url)

            for annotator_id in range(annotator_no):
                if os.path.exists(annotation_project_root + info[0] + '/' +
                                  'a' + str(annotator_id + 1) + '_r' + str(item[0]) + "_annotation.txt") and \
                        sum(numpy.loadtxt(annotation_project_root + info[0] + '/' +
                                          'a' + str(annotator_id + 1) + '_r' + str(item[0]) + "_annotation.txt")) > 0:
                    region_image_url = annotation_project_root + info[0] + '/' + 'a' + str(annotator_id + 1) + \
                                       '_r' + str(item[0]) + "_boundary.txt"
                    region_image = numpy.loadtxt(region_image_url, delimiter=",", dtype=int)
                    write_path = export_path + 'a' + str(annotator_id + 1) + '/' + info[0] + '/'
                    if not os.path.exists(write_path):
                        os.mkdir(write_path)

                    annotator_data_url = annotation_project_root + info[0] + '/' + \
                                         'a' + str(annotator_id + 1) + '_' + 'r' + str(item[0]) + "_annotation.txt"
                    annotator_data = numpy.loadtxt(annotator_data_url, delimiter=",", dtype=int)

                    write_url = export_path + 'a' + str(annotator_id + 1) + '/' + info[0] + '/' \
                                + '_' + 'r' + str(item[0]) + '_original.png'
                    cv2.imwrite(write_url, original_pic)

                    mask = numpy.zeros(original_pic.shape)
                    mask_original = numpy.zeros(original_pic.shape)

                    for i, val in enumerate(annotator_data):
                        if i != 1 and val != 0:
                            mask[region_image == i] = colour[int(val) - 1]
                            mask_original[region_image == i] = (original_pic[region_image == i] * 2.7
                                                                + colour[val - 1]) / 3.3
                        else:
                            mask_original[region_image == i] = original_pic[region_image == i]

                    write_url = export_path + 'a' + str(annotator_id + 1) + '/' + info[0] + '/' \
                                + '_' + 'r' + str(item[0]) + '_mask.png'
                    cv2.imwrite(write_url, mask)

                    mask_original[region_image == -1] = tuple([0, 0, 0])
                    write_url = export_path + 'a' + str(annotator_id + 1) + '/' + info[0] + '/' \
                                + '_' + 'r' + str(item[0]) + '_mask_original.png'
                    cv2.imwrite(write_url, mask_original)

                    write_url = export_path + 'a' + str(annotator_id + 1) + '/' + info[0] + '/' \
                                + '_' + 'r' + str(item[0]) + '_annotator_data.txt'
                    numpy.savetxt(write_url, annotator_data, fmt="%d", delimiter=",")

                    write_url = export_path + 'a' + str(annotator_id + 1) + '/' + info[0] + '/' \
                                + '_' + 'r' + str(item[0]) + '_boundary.txt'
                    numpy.savetxt(write_url, region_image, fmt="%d", delimiter=",")

    annotator_no = 6
    for annotator_id in range(annotator_no):
        if not os.listdir(export_path + 'a' + str(annotator_id + 1)):
            shutil.rmtree(export_path + 'a' + str(annotator_id + 1))
    if os.listdir(export_path):
        make_archive_threadsafe(export_file, export_path)
    return export_file


def export_freehand_annotation_data(manifest_file_url, manifest_txt=None, export_file=None):
    annotation_project_root = freehand_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4] + '/'
    if manifest_txt != None:
        export_annotation_root_temp = "static/cache/" + str(uuid.uuid4()) + "/"
        if export_file == None:
            export_file = export_annotation_root_temp.replace("/cache", "")[:-1] + '.zip'
        print(export_file)
        if os.path.exists(export_file):
            os.remove(export_file)

        export_path = export_annotation_root_temp
        if os.path.exists(export_path):
            shutil.rmtree(export_path)
        os.mkdir(export_path)
    else:
        manifest_txt = open(manifest_file_url).readlines()

        if not (not (manifest_file_url.rsplit("/", 1)[1][:-4] == "") and not (
                manifest_file_url.rsplit("/", 1)[1][:-4] is None)):
            print(manifest_file_url.rsplit("/", 1)[1][:-4])
            return
        export_file = export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4] + '_freehand_annotation.zip'
        if os.path.exists(export_file):
            os.remove(export_file)

        export_path = export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4] + '/freehand_annotation/'
        if os.path.exists(export_path):
            shutil.rmtree(export_path)
        elif not os.path.exists(export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4]):
            os.mkdir(export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4])
        os.mkdir(export_path)

    annotator_no = 6
    for annotator_id in range(annotator_no):
        os.mkdir(export_path + 'a' + str(annotator_id + 1) + '/')

    down = 4
    down_save = 32
    wsi_count = 1
    # print(manifest_txt)
    for wsi in manifest_txt:
        print(wsi)
        print(time.asctime(time.localtime(time.time())),
              "start export freehand annotation:" + str(wsi_count) + '/' + str(len(manifest_txt)))
        wsi_count += 1
        info = wsi.split('\t')
        if not os.path.exists(annotation_project_root + info[0] + '/'):
            continue
        dimensions = None
        for annotator_id in range(annotator_no):
            if os.path.exists(annotation_project_root + info[0] + '/' +
                              'a' + str(annotator_id + 1) + '.db') and \
                    len(freehand_annotation_sqlite.SqliteConnector(annotation_project_root + info[0] + '/' +
                                        'a' + str(annotator_id + 1) + '.db').get_lines()) > 0:
                if not dimensions:
                    try:
                        dimensions = openslide.open_slide(original_data_root + info[0] + '/' + info[1]).dimensions
                    except Exception as e:
                        print('Error:', e)
                        continue

                img_height = dimensions[1]
                img_width = dimensions[0]

                if not os.path.exists(export_path + 'a' + str(annotator_id + 1) + '/' + 'Background'):
                    os.mkdir(export_path + 'a' + str(annotator_id + 1) + '/' + 'Background')

                oslide = openslide.OpenSlide(original_data_root + info[0] + '/' + info[1])
                level = oslide.get_best_level_for_downsample(16)
                reading_size = [int(img_width / oslide.level_downsamples[level]),
                                int(img_height / oslide.level_downsamples[level])]
                try:
                    mask = oslide.read_region((0, 0), level, reading_size)
                except Exception as e:
                    print('Error:', e)
                    continue

                mask = numpy.array(mask)
                mask = cv2.resize(mask, (int(img_width / 16), int(img_height / 16)))
                r, g, b, a = cv2.split(mask)
                mask = cv2.merge([r, g, b])

                mask = cv2.cvtColor(mask, cv2.COLOR_RGB2GRAY)
                mask = cv2.GaussianBlur(mask, (61, 61), 0)
                ret, mask = cv2.threshold(mask, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                write_url = export_path + 'a' + str(annotator_id + 1) + '/' + 'Background' + '/' \
                            + info[0] + '.png'
                mask = cv2.resize(mask, (int(img_width / down_save), int(img_height / down_save)))
                cv2.imwrite(write_url, mask)
                oslide.close()

                db = freehand_annotation_sqlite.SqliteConnector(
                    annotation_project_root + info[0] + '/' + 'a' + str(annotator_id + 1) + '.db')
                for grade in range(1, 5):
                    mask = numpy.zeros([int(img_height / down), int(img_width / down), 1], numpy.uint8)
                    if not os.path.exists(export_path + 'a' + str(annotator_id + 1) + '/' + 'Grade' + str(grade)):
                        os.mkdir(export_path + 'a' + str(annotator_id + 1) + '/' + 'Grade' + str(grade))

                    for temp in db.get_lines():
                        if temp[5] != grade:
                            continue
                        if temp[1] < down_save:
                            temp1 = down_save
                        elif temp[1] >= img_width - down_save:
                            temp1 = img_width - down_save
                        else:
                            temp1 = temp[1]

                        if temp[2] < down_save:
                            temp2 = down_save
                        elif temp[2] >= img_height - down_save:
                            temp2 = img_height - down_save
                        else:
                            temp2 = temp[2]

                        if temp[3] < down_save:
                            temp3 = down_save
                        elif temp[3] >= img_width - down_save:
                            temp3 = img_width - down_save
                        else:
                            temp3 = temp[3]

                        if temp[4] < down_save:
                            temp4 = down_save
                        elif temp[4] >= img_height - down_save:
                            temp4 = img_height - down_save
                        else:
                            temp4 = temp[4]

                        cv2.line(mask, (int(temp1 / down), int(temp2 / down)),
                                 (int(temp3 / down), int(temp4 / down)), 255, 4)
                    # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                    # mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

                    # contours, hierarchy = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    # cv2.drawContours(mask, contours, -1, 255, -1)
                    #
                    # mask_new = mask.copy()
                    # contours_new, hierarchy_new = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    # cv2.drawContours(mask_new, contours_new, -1, 255, -1)
                    #
                    # while not (mask_new == mask).all():
                    #     mask = mask_new.copy()
                    #     contours_new, hierarchy_new = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    #     cv2.drawContours(mask_new, contours_new, -1, 255, -1)
                    #
                    # mask = mask_new.copy()

                    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
                    mask = numpy.zeros([int(img_height / down), int(img_width / down), 1], numpy.uint8)
                    # print(hierarchy)
                    for index in range(len(contours)):
                        if hierarchy[0][index][3] != -1:
                            cv2.drawContours(mask, contours, index, 255, -1)

                    # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
                    # mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

                    write_url = export_path + 'a' + str(annotator_id + 1) + '/' + 'Grade' + str(grade) + '/' \
                                + info[0] + '.png'
                    mask = cv2.resize(mask, (int(img_width / down_save), int(img_height / down_save)))
                    cv2.imwrite(write_url, mask)

                contours_list = []
                for grade in range(1, 5):
                    temp = cv2.imread(export_path + 'a' + str(annotator_id + 1) + '/' + 'Grade' + str(grade) + '/' \
                                      + info[0] + '.png', 0)
                    contours, hierarchy = cv2.findContours(temp, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
                    contours_list.append(contours)

                mask = numpy.zeros([int(img_height / down_save), int(img_width / down_save), 3], numpy.uint8)

                color = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 0, 0)]
                for loop_times in range(5):
                    for grade in range(4):
                        contours_temp = contours_list[grade].copy()
                        for index in range(len(contours_temp)):
                            mask_new = mask.copy()
                            cv2.drawContours(mask_new, contours_temp, index, color[grade], 1)
                            if not (mask_new == mask).all():
                                cv2.drawContours(mask_new, contours_temp, index, color[grade], -1)
                                mask = mask_new.copy()
                            else:
                                for i in range(len(contours_list[grade])):
                                    try:
                                        if ((contours_list[grade][i]) == (contours_temp[index])).all():
                                            contours_list[grade].pop(i)
                                            break
                                    except:
                                        if (contours_list[grade][i]) == (contours_temp[index]):
                                            contours_list[grade].pop(i)
                                            break
                if not os.path.exists(export_path + 'a' + str(annotator_id + 1) + '/' + 'summary'):
                    os.mkdir(export_path + 'a' + str(annotator_id + 1) + '/' + 'summary')
                write_url = export_path + 'a' + str(annotator_id + 1) + '/' + 'summary' + '/' \
                            + info[0] + '.png'
                cv2.imwrite(write_url, mask)

    annotator_no = 6
    for annotator_id in range(annotator_no):
        if not os.listdir(export_path + 'a' + str(annotator_id + 1)):
            shutil.rmtree(export_path + 'a' + str(annotator_id + 1))
    if os.listdir(export_path):
        make_archive_threadsafe(export_file, export_path)
    return export_file


def export_region_annotation_data(manifest_file_url, region_size, manifest_txt=None, export_file=None):
    annotation_project_root = nuclei_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4] + '/'
    if manifest_txt != None:
        export_annotation_root_temp = "static/cache/" + str(uuid.uuid4()) + "/"
        if export_file == None:
            export_file = export_annotation_root_temp.replace("/cache", "")[:-1] + '.zip'
        print(export_file)
        if os.path.exists(export_file):
            os.remove(export_file)

        export_path = export_annotation_root_temp
        if os.path.exists(export_path):
            shutil.rmtree(export_path)
        os.mkdir(export_path)

    else:
        manifest_txt = open(manifest_file_url).readlines()
        if not (not (manifest_file_url.rsplit("/", 1)[1][:-4] == "") and not (
                manifest_file_url.rsplit("/", 1)[1][:-4] is None)):
            return
        export_file = export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4] + '_region_annotation.zip'
        if os.path.exists(export_file):
            os.remove(export_file)

        export_path = export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4] + '/region_annotation/'
        if os.path.exists(export_path):
            shutil.rmtree(export_path)
        elif not os.path.exists(export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4]):
            os.mkdir(export_annotation_root + manifest_file_url.rsplit("/", 1)[1][:-4])
        os.mkdir(export_path)

    wsi_count = 0
    for wsi in manifest_txt:
        print(wsi)
        wsi_count += 1
        print(time.asctime(time.localtime(time.time())),
              "start export nuclei annotation:" + str(wsi_count) + '/' + str(len(manifest_txt)))
        info = wsi.split('\t')
        try:
            svs_file_path = original_data_root + info[0] + '/' + info[1]
            tba_list_db = annotation_project_root + '/' + info[0] + '/' + 'tba_list.db'
            print(svs_file_path)
            if not os.path.exists(tba_list_db):
                continue
            db = nuclei_annotation_sqlite.SqliteConnector(tba_list_db)
            tba_result = db.get_RegionID_Centre()
            if len(tba_result) > 0:
                if not os.path.exists(export_path + info[0]):
                    os.mkdir(export_path + info[0])
                oslide = openslide.OpenSlide(svs_file_path)
                for item in tba_result:
                    patch = oslide.read_region(
                        (item[1] - 256 - int(int(region_size) / 2), item[2] - 256 - int(int(region_size) / 2)),
                        0, (int(region_size), int(region_size)))
                    patch.save(
                        export_path + info[0] + '/' + str(item[0]) + '_' + str(item[1]) + '_' + str(
                            item[2]) + '_' + str(
                            int(region_size)) + '.png')
                oslide.close()
        except Exception as e:
            print("ERROR: ", wsi)
            print(e)

    if os.listdir(export_path):
        make_archive_threadsafe(export_file, export_path)
    return export_file


def refresh_npy():
    global annotation_project_table
    result = []
    available_slide_id = []
    for item in manifest_controller.get_available_slide_id():
        available_slide_id.append(item['id'])
    file_list = os.listdir(manifest_root)
    file_list.sort()
    mani = manifest.Manifest()
    for file in file_list:
        print("start import manifest:", file)
        temp = []
        if file[-4:] != ".txt":
            continue
        slide_table_file = open('export/' + file[:-4] + '_slide_table.txt', 'w')
        slide_id = []
        missing_slide_uuid = []

        project_name = file[:-4]
        temp.append(project_name)

        manifest_txt = open(manifest_root + file).readlines()
        for wsi in manifest_txt:
            info = wsi.split('\t')
            if info[0] == "id":
                continue
            try:
                info[0] = '[*] ' + info[0]
                wsi = mani.get_project_by_uuid(info[0][4:])
                if int(wsi[0]) not in available_slide_id:
                    info[0] = '[' + str(wsi[0]) + '] ' + wsi[1]
                    raise Exception
                if int(wsi[0]) in slide_id:
                    continue
                slide_table_file.write(str(wsi[0]) + '\t' + str(wsi[1]) + '\t' + str(wsi[2]) + '\n')
                slide_id.append(int(wsi[0]))
            except:
                missing_slide_uuid.append(info[0])
        slide_table_file.close()
        # print(missing_slide_uuid)
        # print(slide_id)

        missing_slide_id_str = ""
        slide_id_str = ""
        if not slide_id:
            temp.append('Empty Manifest!')
            result.append(temp)
            continue

        min_slide_id = min(slide_id)
        for i in range(max(slide_id) + 1):
            if i not in slide_id:
                if i >= min_slide_id:
                    missing_slide_id_str = missing_slide_id_str + str(i) + ', '
            elif i - 1 not in slide_id and i in slide_id:
                slide_id_str = slide_id_str + str(i)
                if i + 1 in slide_id:
                    slide_id_str = slide_id_str + '-'
                else:
                    slide_id_str = slide_id_str + ', '
            elif i - 1 in slide_id and i in slide_id and i + 1 not in slide_id:
                slide_id_str = slide_id_str + str(i) + ', '
        temp.append(slide_id_str)
        temp.append(missing_slide_id_str)
        temp.append('<button type="button" onclick="alert(' + str(missing_slide_uuid) +
                    '.join(\'\\n\'))">see more</button>')

        annotation_project_root = nuclei_annotation_root + project_name + '/'
        if not os.path.exists(annotation_project_root):
            os.mkdir(annotation_project_root)

        temp.append("Unavailable")

        annotation_project_root = freehand_annotation_root + project_name + '/'
        if not os.path.exists(annotation_project_root):
            os.mkdir(annotation_project_root)

        temp.append("Unavailable")

        temp.append(
            '<a href="/nuclei_annotation_v2?' + 'project=' + str(project_name)  # '&slide_id=' + str(slide_id[0])
            + '" target="_Blank">nuclei annotate </a>' + '(' +
            '<a href="/nuclei_annotation?' + 'project=' + str(project_name)  # '&slide_id=' + str(slide_id[0])
            + '" target="_Blank">v1 </a>' + ')'
            )
        temp.append('<a href="/freehand_annotation?' + 'project=' + str(project_name)  # '&slide_id=' + str(slide_id[0])
                    + '" target="_Blank">freehand annotate </a>')

        temp.append("Unavailable")
        temp.append("Unavailable")

        temp.append('<a href="' + '/static/export/' + file[:-4] + '_slide_table.txt" ' + \
                    'download="' + file[:-4] + '_slide_table.txt' + '">Available Slides </a>' +
                    '<a href="' + '/available_slide_file/' + file[:-4] + '" ' + \
                    'download="' + file[:-4] + '.txt' + '">Slide List </a>'
                    )

        result.append(temp)

    filename = manifest_root + 'table.npy'
    result = numpy.array(result)
    annotation_project_table = result.copy()
    numpy.save(filename, result)  # 保存为.npy格式

    refresh_freehand_annotation_progress()
    refresh_nuclei_annotation_progress()

    return


def check_freehand_annotation(annotation_file):
    global freehand_annotation_flag
    if not annotation_file in freehand_annotation_flag.keys() or \
            freehand_annotation_flag[annotation_file][1] != os.stat(annotation_file).st_mtime:
        freehand_annotation_flag[annotation_file] = [
            len(freehand_annotation_sqlite.SqliteConnector(annotation_file).get_lines()),
            os.stat(annotation_file).st_mtime]
    return freehand_annotation_flag[annotation_file][0]



annotation_project_table = None
filename = manifest_root + 'table.npy'
if not os.path.exists(filename):
    refresh_npy()
annotation_project_table = numpy.load(filename)
freehand_annotation_flag = {}
