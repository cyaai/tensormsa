from chatbot.common.chat_share_data import ShareData
from cluster.service.service_predict_bilstmcrf import PredictNetBiLstmCrf
import ngram
from chatbot.common.chat_knowledge_mem_dict import ChatKnowledgeMemDict
from collections import Counter
import logging

class EntityRecognizer(ShareData):

    def __init__(self, cb_id, ner_model_id):
        """
        init global variables
        """
        self.cb_id = cb_id
        self.ner_model_id = ner_model_id
        self.bilstmcrf_model = PredictNetBiLstmCrf()

    def parse(self, share_data):
        logging.info("■■■■■■■■■■ NER 분석 전 : " + str(share_data.get_morphed_data()))
        ner_data = self._get_ner_data(' '.join(share_data.get_morphed_data()))
        share_data, ner_data = self._match_ngram_dict(share_data , share_data.get_morphed_data(), ner_data)
        self._get_convert_data(ner_data, share_data)
        logging.info("■■■■■■■■■■ NER 분석 결과 : " + str(ner_data))
        return share_data

    def _get_convert_data(self, ner_data, share_data):
        """
        make sentence for charn cnn intent prediction 
        :param ner_data: 
        :param share_data: 
        :return: 
        """
        buff_list = []
        for val_a, val_b in zip(ner_data, share_data.get_morphed_data()) :
            if(val_a == 'O') :
                buff_list.append(val_b)
            else :
                buff_list.append(val_a)
        share_data.set_convert_data(sorted(set(buff_list), key=lambda x: buff_list.index(x)))

    def _get_ner_data(self, input_sentence):
        result = self.bilstmcrf_model.run(self.ner_model_id, {"input_data": input_sentence, "num": 0, "clean_ans": False})
        return result

    def _match_ngram_dict(self, share_data, input_sentence, ner_data_input):
        """
        match ngram dict with ner analized 
        :return: 
        """
        try :
            result = {}
            ner_data = ner_data_input.copy()
            if (len(input_sentence) != len(ner_data)):
                logging.info("■■■■■■■■■■ 길이 차이로 NER 처리 불가 ■■■■■■■■■■")
                pass

            if(ChatKnowledgeMemDict.ngram.get(self.cb_id) == None):
                cb_data = ChatKnowledgeMemDict.data.get(self.cb_id)
                cb_data_order = ChatKnowledgeMemDict.data_order.get(self.cb_id)
                dist_keys = dict(Counter(ner_data))
                index = 0
                for key, val in zip(ner_data, input_sentence) :
                    if (key == 'O'):
                        continue
                    if (result.get(key)) :
                        continue

                    model = ngram.NGram(list(map(lambda x : x.lower(), cb_data.get(key))))
                    if(dist_keys.get(key) > 1):
                        ner_conv = ' '.join(list(map(lambda x : x[0], list(filter(lambda x : x[1] == key, zip(input_sentence,ner_data))))))
                        ner_conv = ner_conv.lower()
                        result[key] = list(map(lambda x : x[0], model.search(ner_conv.replace(' ',''), threshold=1.0)))
                        if(len(result[key]) == 0) :
                            result[key] = list(map(lambda x : x[0], model.search(ner_conv.replace(' ',''), threshold=0.15)))[0:4]
                        if(len(result[key]) == 0):
                            logging.info("■■■■■■■■■■ NER 오류로 전수 조사 시작 (시간소요발생) ■■■■■■■■■■")
                            data, id = self.check_all_dict(ner_conv.replace(' ',''), cb_data, cb_data_order)
                            if(id != None) :
                                result[id] = data
                                key = id
                                ner_data_input[index] = id
                    else:
                        ner_conv = val.lower()
                        result[key] = list(map(lambda x: x[0], model.search(ner_conv, threshold=1.0)))
                        if (len(result[key]) == 0):
                            result[key] = list(map(lambda x : x[0], model.search(ner_conv, threshold=0.4)))[0:4]
                        if (len(result[key]) == 0):
                            logging.info("■■■■■■■■■■ NER 오류로 전수 조사 시작 (시간소요발생) ■■■■■■■■■■")
                            data, id = self.check_all_dict(ner_conv, cb_data, cb_data_order)
                            if (id != None):
                                result[id] = data
                                key = id
                                ner_data_input[index] = id

                    if(len(result[key]) == 0):
                        del result[key]
                    else :
                        if(key is not None and key == 'tagorg') :
                            share_data.set_story_ner_entity(key, [ner_conv] + result[key])
                        else :
                            share_data.set_story_ner_entity(key, result[key])

                    index = index + 1
            return share_data, ner_data_input
        except Exception as e :
            raise Exception ("Error on matching ngram afger bilstm crf : {0}".format(e))

    def check_all_dict(self, ner_conv, cb_data, cb_data_order):
        """
        check other dict when failed to find matching value
        :param ner_conv: 
        :return: 
        """
        result = []
        for key in cb_data_order :
            model = ngram.NGram(cb_data.get(key))
            result = list(map(lambda x: x[0], model.search(ner_conv, threshold=0.7)))[0:4]
            if(len(result) > 0 ) :
                return result, key
        return result, None