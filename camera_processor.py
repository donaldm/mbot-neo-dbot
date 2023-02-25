import cv2
import torch
import numpy as np
import cv2
import argparse
from time import time, sleep
import os
import sys
from ultralytics import YOLO
import redis

os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS'] = 'rtsp_transport;udp'


class CameraProcessor(object):
    def __init__(self, rtsp_stream, output_video_file_path):
        self.rtsp_stream = rtsp_stream
        self.output_video_file_path = output_video_file_path
        self.stream = cv2.VideoCapture(self.rtsp_stream, cv2.CAP_FFMPEG)
        if not self.stream.isOpened():
            print('Could not open RTSP stream {url}'.format(url=self.rtsp_stream))
            sys.exit(-1)

        self.model = YOLO()

        self.classes = self.model.names
        self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if self.device == 'cpu':
            print('Warning CUDA is not available')

        self.redis = redis.Redis(host='localhost', port=6379)
        self.frame_delay = 0

    def process_video_stream(self):
        assert self.stream.isOpened()
        while True:
            start_time = time()
            ret, frame = self.stream.read()
            assert ret
            results = self.model.predict(frame)
            prediction_list_name = 'predictions'
            for i in range(0, self.redis.llen(prediction_list_name)):
                self.redis.lpop(prediction_list_name)

            for result in results:
                for cls in result.boxes.cls:
                    print(self.model.names[int(cls)])
                    self.redis.lpush('predictions', self.model.names[int(cls)])


            frame = results[0].visualize()

            end_time = time()
            fps = 1/np.round(end_time - start_time, 3)

            cv2.imshow("DBot camera", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

            sleep(self.frame_delay)
        self.stream.release()
        cv2.destroyAllWindows()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--camera_rtsp_url')
    parser.add_argument('--output_video_file_path')

    args = parser.parse_args()

    camera_rtsp_url = args.camera_rtsp_url.strip()
    output_video_file_path = args.output_video_file_path

    camera_process = CameraProcessor(camera_rtsp_url, output_video_file_path)
    camera_process.process_video_stream()


if __name__ == '__main__':
    main()