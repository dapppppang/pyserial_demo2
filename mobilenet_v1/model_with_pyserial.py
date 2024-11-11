import torch
import torch.nn as nn
from pyserial_demo.pyserial_demo2 import uart_setup, send_weight, send_tensor, receive_data



class DepthwiseSeparableConv(nn.Module):
    def __init__(self, in_channels, out_channels, stride=1):
        super(DepthwiseSeparableConv, self).__init__()
        self.depthwise = nn.Conv2d(in_channels, in_channels, kernel_size=3, stride=stride, padding=1, groups=in_channels, bias=False)      # already done by FPGA
        self.pointwise = nn.Conv2d(in_channels, out_channels, kernel_size=1, stride=1, padding=0, bias=False)
        self.bn = nn.BatchNorm2d(out_channels)
        self.relu = nn.ReLU(inplace=True)

    def forward(self, x, sw=True):
        if sw:
            x = self.depthwise(x)      # already done by FPGA
        x = self.pointwise(x)
        x = self.bn(x)
        return self.relu(x)


class MobileNetV1_with_pyserial(nn.Module):
    def __init__(self, num_classes=10):
        super(MobileNetV1_with_pyserial, self).__init__()
        # MobileNetV1 레이어 정의
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, stride=1, padding=1, bias=False)
        self.bn1 = nn.BatchNorm2d(32)
        self.relu = nn.ReLU(inplace=True)

        # Depthwise Separable Convolutions
        self.conv2 = DepthwiseSeparableConv(32, 64, stride=1)
        self.conv3 = DepthwiseSeparableConv(64, 128, stride=2)
        self.conv4 = DepthwiseSeparableConv(128, 128, stride=1)
        self.conv5 = DepthwiseSeparableConv(128, 256, stride=2)
        self.conv6 = DepthwiseSeparableConv(256, 256, stride=1)
        self.conv7 = DepthwiseSeparableConv(256, 512, stride=2)

        # 반복되는 512 레이어
        self.conv8 = DepthwiseSeparableConv(512, 512, stride=1)
        self.conv9 = DepthwiseSeparableConv(512, 512, stride=1)
        self.conv10 = DepthwiseSeparableConv(512, 512, stride=1)
        self.conv11 = DepthwiseSeparableConv(512, 512, stride=1)
        self.conv12 = DepthwiseSeparableConv(512, 512, stride=1)

        # 최종 1024 레이어
        self.conv13 = DepthwiseSeparableConv(512, 1024, stride=2)
        self.conv14 = DepthwiseSeparableConv(1024, 1024, stride=1)

        # 평균 풀링 및 최종 분류 레이어
        self.avg_pool = nn.AdaptiveAvgPool2d(1)
        self.fc = nn.Linear(1024, num_classes)

    def forward(self, x):

        # 초기 Conv 레이어
        x = self.conv1(x)
        x = self.bn1(x)
        x = self.relu(x)


        # UART PORT OPEN
        ser = uart_setup()

        # SEND INSTRUCTION
        instruction1 = 0b10101000
        byte_to_send1 = instruction1.to_bytes(1, byteorder='big')  # 1바이트로 변환
        ser.write(byte_to_send1)  # SEND INSTRUCTION (type : bytes)

        # SEND WEIGHT TENSOR
        send_weight(ser, 'weight_binary_files/fp32/dwcv2_weight_bin.bin')  # SEND WEIGHT BINARY STRING DATA

        # SEND INSTRUCTION
        instruction2 = 0b00100000
        byte_to_send2 = instruction2.to_bytes(1, byteorder='big')  # 1바이트로 변환
        ser.write(byte_to_send2)  # SEND INSTRUCTION (type : bytes)

        # SEND OUTPUT TENSOR
        send_tensor(ser, x, torch.float32)

        # RECEIVE RESULT OF FPGA
        x = receive_data(ser, (1, 32, 32, 32), torch.float32)
        ser.close()

        # Depthwise Separable Conv 레이어들
        x = self.conv2(x, sw=False)
        print("conv2!")
        x = self.conv3(x)
        print("conv3!")
        x = self.conv4(x)
        print("conv4!")
        x = self.conv5(x)
        print("conv5!")
        x = self.conv6(x)
        print("conv6!")
        x = self.conv7(x)

        print("conv7!")
        # 반복되는 512 레이어들
        x = self.conv8(x)
        print("conv8!")
        x = self.conv9(x)
        print("conv9!")
        x = self.conv10(x)
        print("conv10!")
        x = self.conv11(x)
        print("conv11!")
        x = self.conv12(x)
        print("conv12!")

        # 최종 Conv 레이어
        x = self.conv13(x)
        print("conv13!")
        x = self.conv14(x)
        print("conv14!")

        # 평균 풀링
        x = self.avg_pool(x)
        print("avg_pool!")

        # 벡터화 및 FC 레이어로 연결
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        print("fc")

        return x
