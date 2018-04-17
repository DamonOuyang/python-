# from selenium import webdriver
# from selenium.webdriver.common.action_chains import ActionChains
import requests as req
from lxml import etree
import json
from io import BytesIO
from PIL import Image,ImageTk
import json
from pprint import pprint
import re
import urllib.parse
import time
import warnings
import tkinter
from prettytable import PrettyTable
import prettytable
import datetime


warnings.filterwarnings('ignore')
#流程分为：登录->查票->提交->选择乘客->买票
class catchTickets(object):

    def __init__(self):
        self.general_headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
                            }
        self.headers2={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
         'Referer':'https://kyfw.12306.cn/otn/leftTicket/init',
         'Accept': '*/*',
        'Accept-Encoding': 'gzip, deflate',
        'Accept-Language': 'zh-CN,zh;q=0.9',
        'X-Requested-With': 'XMLHttpRequest',
        'Connection': 'keep-alive',
        'Origin': 'https://kyfw.12306.cn',
        'Host': 'kyfw.12306.cn',
        'Upgrade-Insecure-Requests': '1',
        'Cache-Control': 'max-age=0',
        'If-Modified-Since': '0'
        }
        self.headers3={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
         'Referer': 'https://kyfw.12306.cn/otn/passport?redirect=/otn/login/userLogin',
        }
        self.headers4={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/65.0.3325.181 Safari/537.36',
            'Referer': 'https://kyfw.12306.cn/otn/confirmPassenger/initDc'
        }
        self.signin_state=False
        self.Session=req.session()
        self.start_date='2018-04-18'
        self.from_station_id=''
        self.to_station_id=''
        self.purpose_code='ADULT'
        self.tickets_info=[]
        self.passengers_info={}
        self.station_map=self.Session.get('https://kyfw.12306.cn/otn/resources/js/framework/station_name.js?station_version=1.9002',verify=False).text
        self.selected_info=[]

    def img_check(self):
        response=self.Session.get('https://kyfw.12306.cn/passport/captcha/captcha-image?login_site=E&module=login&rand=sjrand&0.6134406544816635',headers=self.general_headers,verify=False)
        img_stream=Image.open(BytesIO(response.content))
        return img_stream


    def login(self,uname,pwd,pos):
        from_data_sign={'username':uname,'password':pwd,'appid':'otn'}
        form_data_chk={'login_site':'E','rand':'sjrand'}
        # response=self.Session.get('https://kyfw.12306.cn/passport/captcha/captcha-image?login_site=E&module=login&rand=sjrand&0.6134406544816635',headers=self.general_headers,verify=False)
        # img=Image.open(BytesIO(response.content))
        # img.show()
        # get_input=input('输入正确图片编号:')
        # if ',' in get_input:
        #     select_list=get_input.split(',')
        # else:
        #     select_list=get_input
        # pos=[]
        # for ind in select_list:
        #     i=int(ind)
        #     if i<5:
        #         x=45+(i-1)*70
        #         y=50
        #     else:
        #         x=45+(i-5)*70
        #         y=120
        #     pos.extend([x,y])
        # print(pos)
        form_data_chk['answer']=str(pos)[1:-1]
        response=self.Session.post('https://kyfw.12306.cn/passport/captcha/captcha-check',
                        headers=self.headers2,data=form_data_chk,verify=False)
        if json.loads(response.text)['result_code']=='4':
            response=self.Session.post('https://kyfw.12306.cn/passport/web/login',headers=self.headers2,data=from_data_sign,verify=False)
            if json.loads(response.text)['result_code']=='0' or (not json.loads(response.text)['result_code']):
                self.signin_state=True
                print('signin sucessful')
                self.Session.post('https://kyfw.12306.cn/otn/login/userLogin',headers=self.general_headers,data={'_json_att':''},verify=False)
                response=self.Session.post('https://kyfw.12306.cn/passport/web/auth/uamtk',headers=self.headers3,verify=False,data={'appid':'otn'})
                self.Session.post('https://kyfw.12306.cn/otn/uamauthclient',headers=self.headers3,data={'tk':json.loads(response.text)['newapptk']})
                return 1
            else:
                print('username or password wrong')
                return -1
        else:
            print('verify faild')
            return -2

    def get_passenger_info(self):
        response=self.Session.get('https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs',headers=self.headers2,verify=False)
        return json.loads(response.text)['data']['normal_passengers']

    def get_station_info(self,from_station,to_station):
        pattern1=re.compile("%s\|(\w+)"%from_station)
        pattern2=re.compile("%s\|(\w+)"%to_station)
        try:
            m1=re.search(pattern1,self.station_map)
            m2=re.search(pattern2,self.station_map)
            self.from_station_id=m1.group(1)
            self.to_station_id=m2.group(1)
            print(self.from_station_id,self.to_station_id)
            return True
        except:
            print('no station infomation')
            return False

    def select_tickets(self,start_station,end_station):
        #高级软卧||软卧|||无座||硬卧|硬座|二等座|一等座|特等座||||
        if self.get_station_info(start_station,end_station):

            ticket_data_form={
                'secretStr':'',
                'train_date':self.start_date,
                'back_train_date':'2018-03-31',
                'tour_flag':'dc',
                'purpose_codes':'ADULT',
                'query_from_station_name':'',
                'query_to_station_name':'',
                'undifined':''
                }

            #获取列车信息
            self.Session.get('https://kyfw.12306.cn/otn/leftTicket/init',headers=self.general_headers,verify=False)
            response=self.Session.get('https://kyfw.12306.cn/otn/leftTicket/query?leftTicketDTO.train_date=%s&leftTicketDTO.from_station=%s&leftTicketDTO.to_station=%s&purpose_codes=ADULT'%(self.start_date,self.from_station_id,self.to_station_id),headers=self.headers2,verify=False)
            raw_data=json.loads(response.text)['data']['result']
            # pprint(raw_data)
            for r in raw_data:
                buff=[]
                raw_list=r.split('|')
                buff.append(urllib.parse.unquote(raw_list[0]))
                buff+=raw_list[3:11]
                pattern1=re.compile("(\w+)\|%s"%buff[4])
                pattern2=re.compile("(\w+)\|%s"%buff[5])
                m1=re.search(pattern1,self.station_map)
                m2=re.search(pattern2,self.station_map)
                buff[4]=m1.group(1)
                buff[5]=m2.group(1)
                buff.append(raw_list[12])
                buff.append(raw_list[21])
                buff.append(raw_list[23])
                buff.append(raw_list[26])
                buff+=raw_list[28:33]
                buff.append(raw_list[2])
                buff.append(raw_list[15])
                self.tickets_info.append(buff)
            t=PrettyTable(['编号','车次','起点站','终点站','发车时间','到站时间','历经时间','高级软卧','软卧','硬卧','特等座','一等座','二等座','硬座','无座'])
            t.header =True
            t.align['无座']='l'
            t.vrules =prettytable.ALL
            index=0
            for ticket in self.tickets_info:
                index+=1
                t.add_row([index,ticket[1],ticket[4],ticket[5],ticket[6],ticket[7],ticket[8],ticket[10],ticket[11],ticket[13],ticket[17],ticket[16],ticket[15],ticket[14],ticket[12]])
            print(t)
            time.sleep(2)
            train_index=int(input('inout train number:'))
            self.selected_info=[self.tickets_info[train_index-1][1],self.tickets_info[train_index-1][4],self.tickets_info[train_index-1][5]]
            response=self.Session.post('https://kyfw.12306.cn/otn/login/checkUser',data={'_json_att':''},headers=self.headers2,verify=False)
            # pprint(response.text)
            ticket_data_form['secretStr']=self.tickets_info[train_index-1][0]

            #提交选定列车
            ticket_data_form['query_from_station_name']=self.selected_info[1]
            ticket_data_form['query_to_station_name']=self.selected_info[2]
            response=self.Session.post('https://kyfw.12306.cn/otn/leftTicket/submitOrderRequest',headers=self.headers2,data=ticket_data_form,verify=False)
            # pprint(response.text)   #为json的返回代表提交订单成功

            #提交成功
            if json.loads(response.text)['status']==True:
                print('----------------------------------选择车次成功!----------------------------')
                response=self.Session.post("https://kyfw.12306.cn/otn/confirmPassenger/initDc",headers=self.headers2,data={'_json_att':''},verify=False)
                pattern=re.compile("globalRepeatSubmitToken.+'(\w+)'?")
                pattern2=re.compile("leftTicketStr':'(.+?)'")
                pattern3=re.compile("key_check_isChange':'(.+?)'")
                m=re.search(pattern,response.text)
                repeatToken=m.group(1)
                m=re.search(pattern2,response.text)
                leftTicket=m.group(1)
                m=re.search(pattern3,response.text)
                key_check_isChange=m.group(1)
                response=self.Session.post('https://kyfw.12306.cn/otn/confirmPassenger/getPassengerDTOs',headers=self.headers4,data={'_json_att':'','REPEAT_SUBMIT_TOKEN':repeatToken},verify=False)
                # pprint(json.loads(response.text))
                self.passengers_info=json.loads(response.text)['data']['normal_passengers']
                print(self.passengers_info)
                t=PrettyTable(['index','name','gender','id_no'])
                t.border=True
                t.padding_width=1
                p_index=0
                for p in self.passengers_info:
                    p_index+=1
                    t.add_row([p_index,p['passenger_name'],p['sex_name'],p['passenger_id_no']])
                print(t)
                select_str=input('请选择乘车人编号，选择多个时以"，"间隔：')
                if select_str:
                    if len(select_str)>1:
                        self.select_passenger=list(map(int,select_str.split(',' if ',' in select_str else '，')))
                    else:
                        self.select_passenger=[int(select_str)]

                print('-------------------------------get passengers sucessful!----------------------------------')

                # O为二等座  M为一等座  9为商务坐  1为硬座  3为硬卧  4为软卧
                seat_list=['','4','','3','1','O','M','9']
                bit_map=['高级软卧','软卧','无座','硬卧','硬座','二等座','一等座','商务座']
                seat_str=''
                i=0
                for t in self.tickets_info[train_index-1][10:18]:
                    if  t=='' or t=='无':
                        bit_map[i]=''
                    i+=1

                for i in bit_map:
                    if i!='':
                        seat_str+='%d.%s '%(bit_map.index(i)+1,i)
                self.seat_type=seat_list[int(input('请选择作为类型：%s:\n'%seat_str))-1]

                comfirm_data1={
                    'cancel_flag':2,
                    'bed_level_order_num':'000000000000000000000000000000',
                    'passengerTicketStr':'%s,0,1,%s,1,%s,%s,N'%(self.seat_type,self.passengers_info[self.select_passenger[0]]['passenger_name'],self.passengers_info[self.select_passenger[0]]['passenger_id_no'],self.passengers_info[self.select_passenger[0]]['mobile_no']),
                    'oldPassengerStr':'%s,1,%s,1_'%(self.passengers_info[0]['passenger_name'],self.passengers_info[0]['passenger_id_no']),
                    'tour_flag':'dc',
                    'randCode':'',
                    'whatsSelect':1,
                    '_json_att':'',
                    'REPEAT_SUBMIT_TOKEN':repeatToken
                }

                train_date=datetime.datetime.strptime(self.start_date,"%Y-%m-%d").strftime("%a %b %d %Y")+' 00:00:00 GMT+0800 (马来西亚半岛标准时间)'
                comfirm_data2={
                    # 'train_date':'Fri Apr 13 2018 00:00:00 GMT+0800 (马来西亚半岛标准时间)',
                    'train_date':train_date,
                    'train_no':self.tickets_info[train_index-1][-2],
                    'stationTrainCode':self.selected_info[0],
                    'seatType':'O',
                    'fromStationTelecode':self.from_station_id,
                    'toStationTelecode':self.to_station_id,
                    'leftTicket':leftTicket,
                    'purpose_codes':'00',
                    'train_location':self.tickets_info[train_index-1][-1],
                    '_json_att':'',
                    'REPEAT_SUBMIT_TOKEN':repeatToken
                }
                comfirm_data3={
                    'passengerTicketStr':'%s,0,1,%s,1,%s,%s,N'%(self.seat_type,self.passengers_info[self.select_passenger[0]]['passenger_name'],self.passengers_info[self.select_passenger[0]]['passenger_id_no'],self.passengers_info[self.select_passenger[0]]['mobile_no']),
                    'oldPassengerStr':'%s,1,%s,1_'%(self.passengers_info[0]['passenger_name'],self.passengers_info[0]['passenger_id_no']),
                    'randCode':'',
                    'purpose_codes':'00',
                    'key_check_isChange':key_check_isChange,
                    'leftTicketStr':leftTicket,
                    'train_location':self.tickets_info[train_index-1][-1],
                    'choose_seats':'',
                    'seatDetailType':'000',
                    'whatsSelect':1,
                    'roomType':'00',
                    'dwAll':'N',
                    '_json_att':'',
                    'REPEAT_SUBMIT_TOKEN':repeatToken

                }
                print('-------------------------------------comfirm order steps(total 5 steps):---------------------------------------------')
                response=self.Session.post('https://kyfw.12306.cn/otn/confirmPassenger/checkOrderInfo',headers=self.headers4,verify=False,data=comfirm_data1)
                # print(response.text)
                print('--------------------------------------step 1 sucessful---------------------------------------')
                response=self.Session.post('https://kyfw.12306.cn/otn/confirmPassenger/getQueueCount',headers=self.headers4,data=comfirm_data2,verify=False)
                # print(response.text)
                print('----------------------------------------step 2 sucessful---------------------------------------')
                time.sleep(3)
                response=self.Session.post('https://kyfw.12306.cn/otn/confirmPassenger/confirmSingleForQueue',headers=self.headers4,data=comfirm_data3,verify=False)
                # pprint(response.text)
                if json.loads(response.text)['status']=='true' or True:
                    print('----------------------------------------step 3 sucessful---------------------------------------')
                    print('车票购买成功')
                # url_str='https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?random=%s&tourFlag=dc&_json_att=&REPEAT_SUBMIT_TOKEN=%s' %(int(time.time()),repeatToken)
                # response=self.Session.get(url_str,headers=self.headers4,verify=False)
                # print('wait1:',response.text)
                # print('----------------------------------------step 4 sucessful---------------------------------------')
                # time.sleep(3)
                # response=self.Session.get('https://kyfw.12306.cn/otn/confirmPassenger/queryOrderWaitTime?random=%s&tourFlag=dc&_json_att=&REPEAT_SUBMIT_TOKEN=%s'%(int(time.time()),repeatToken),headers=self.headers4,verify=False)
                # orderId=json.loads(response.text)['data']['orderId']
                # print('wait2:',response.text)
                # print('----------------------------------------step 5 sucessful---------------------------------------')
                # comfirm_data4={
                #     'orderSequence_no':orderId,
                #     '_json_att':'',
                #     'REPEAT_SUBMIT_TOKEN':repeatToken
                # }
                # response=self.Session.post('https://kyfw.12306.cn/otn/confirmPassenger/resultOrderForDcQueue',headers=self.headers4,data=comfirm_data4,verify=False)
                # print('result:',response.text)
            else:
                print('选择列车失败!!')
               


    def run(self):
        self.login(self.username,self.password,1)
        # self.__select_tickets()
        # self.__get_passenger_info()


class Display(object):

    def __init__(self):
        self.user=catchTickets()
        self.pos_list=[]

    def __login_12306(self):
        self.root=tkinter.Tk()
        self.root.title('Login')
        self.login_state=False
        frame=tkinter.Frame(self.root,width=700,height=540,bg='linen')
        frame.pack()
        tkinter.Label(self.root,bg='linen',fg='Gray',text='Username',width=10).place(x=150,y=160)
        tkinter.Label(self.root,bg='linen',fg='Gray',text='Password',width=10).place(x=150,y=210)
        self.username_input=tkinter.Entry(self.root,width=20)
        self.username_input.place(x=240,y=160)
        self.pwd_input=tkinter.Entry(self.root,show='*',width=20)
        self.pwd_input.bind('<Return>',self.__keyboard_detect)
        self.pwd_input.place(x=240,y=210)

        tkinter.Label(self.root,bg='linen',fg='Gray',text='验证码',width=10).place(x=150,y=260)
        #x:5-280 275  y:40-180 140
        self.chk_canvas=tkinter.Canvas(self.root,width=280,height=180)
        self.chk_canvas.place(x=247,y=260)
        pil_img=self.user.img_check()
        chk_img=ImageTk.PhotoImage(pil_img)
        self.chk_canvas.create_image(150,100,image=chk_img,tag='pic')
        self.chk_canvas.bind('<Button-1>',self.__get_pos)
        # chek_img_wid=tkinter.Label(self.root,image=chk_img)
        # chek_img_wid.bind('<Button-1>',self.__get_pos)
        # chek_img_wid.place(x=240,y=260)
        tkinter.Button(self.root,bg='Gray',fg='whitesmoke',text='刷新',width=8,command=self.__refresh_chkimg).place(x=500,y=200)
        tkinter.Button(self.root,bg='Gray',fg='whitesmoke',text='Login',width=8,command=self.__auth).place(x=400,y=480)
        self.root.mainloop()

    def __keyboard_detect(self):
        self.__auth()

    def __get_pos(self,event):
        self.pos_list.extend([event.x+7,event.y-40])
        self.chk_canvas.create_oval(event.x-7,event.y-7,event.x+7,event.y+7,fill='red')
        print(self.pos_list)
        

    def __auth(self):
        self.login_state=self.user.login(self.username_input.get(),self.pwd_input.get(),self.pos_list)
        if self.login_state:
            self.root.destroy()


    def __refresh_chkimg(self):
        print('refresh')
        # self.chk_canvas.delete('pic')
        self.pos_list.clear()
        pil_img=self.user.img_check()
        chk_img=ImageTk.PhotoImage(pil_img)
        self.chk_canvas.create_image(150,100,image=chk_img,tag='pic')
        self.chk_canvas.update()
        self.root.mainloop()

    def __station(self):
        start=input('请输入乘车起点：')
        end=input('请输入乘车终点：')
        self.user.select_tickets(start,end)


    def __call__(self):
        self.__login_12306()
        if self.login_state:
            self.__station()


if __name__=='__main__':
    ui=Display()
    ui()


