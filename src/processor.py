import collections
import os.path
import pickle
import base64
from progress.counter import Counter
from progress.bar import IncrementalBar

from src import helpers
from src.service import Service

_progressPadding = 29


class Processor:
    # Talk to google api, fetch results and decorate them
    def __init__(self):
        self.service = Service().instance()
        self.user_id = "me"
        self.messagesQueue = collections.deque()
        self.failedMessagesQueue = collections.deque()

    def get_messages(self):
        # Get all messages of user from PROMOTIONS category
        # Output format:
        # [{'id': '13c...7', 'threadId': '13c...7'}, ...]

        response = self.service.users().messages().list(
            userId=self.user_id,
            labelIds=['CATEGORY_PROMOTIONS']  # Добавляем фильтр по категории промоакций
        ).execute()
        
        messages = []
        est_max = response["resultSizeEstimate"] * 5

        progress = Counter(
            f"{helpers.loader_icn} Fetching promotional messages ".ljust(_progressPadding, " ")
        )

        if "messages" in response:
            messages.extend(response["messages"])

        while "nextPageToken" in response and len(messages) < 300:
            page_token = response["nextPageToken"]

            response = (
                self.service.users()
                .messages()
                .list(
                    userId=self.user_id, 
                    pageToken=page_token,
                    labelIds=['CATEGORY_PROMOTIONS']  # Также добавляем фильтр здесь
                )
                .execute()
            )
            messages.extend(response["messages"])

            progress.next()

        progress.finish()

        return messages[:300]

    def process_message(self, request_id, response, exception):
        if exception is not None:
            self.failedMessagesQueue.append(exception.uri)
            return

        headers = response["payload"]["headers"]

        _date = next(
            (header["value"] for header in headers if header["name"] == "Date"), None
        )
        _from = next(
            (header["value"] for header in headers if header["name"] == "From"), None
        )

        self.messagesQueue.append(
            {
                "id": response["id"],
                "labels": response["labelIds"],
                "fields": {"from": _from, "date": _date},
            }
        )

    def get_metadata(self, messages):
        # Get metadata for all messages:
        # 1. Create a batch get message request for all messages
        # 2. Process the returned output
        #
        # Output format:
        # {
        #   'id': '16f....427',
        #   'labels': ['UNREAD', 'CATEGORY_UPDATES', 'INBOX'],
        #   'fields': [
        #     {'name': 'Date', 'value': 'Tue, 24 Dec 2019 22:13:09 +0000'},
        #     {'name': 'From', 'value': 'Coursera <no-reply@t.mail.coursera.org>'}
        #   ]
        # }

        # if os.path.exists("success.pickle"):
        #     with open("success.pickle", "rb") as token:
        #         self.messagesQueue = pickle.load(token)
        #         return

        progress = IncrementalBar(
            f"{helpers.loader_icn} Fetching messages meta data ".ljust(
                _progressPadding, " "
            ),
            max=len(messages),
        )

        batch_size = 100  # максимальный размер пакета, ограниченный Google API
        
        for i in range(0, len(messages), batch_size):
            batch = self.service.new_batch_http_request(callback=self.process_message)
            batch_messages = messages[i:i + batch_size]
            
            for message in batch_messages:
                msg_id = message['id']
                request = self.service.users().messages().get(
                    userId=self.user_id,
                    id=msg_id,
                    format='metadata',
                    metadataHeaders=['From', 'To', 'Date', 'Subject']
                )
                batch.add(request)
            
            batch.execute()
            progress.next(len(batch_messages))

        progress.finish()

    def get_newsletters(self):
        """Получает список всех рассылок из сообщений"""
        newsletters = {}
        
        for message in self.messagesQueue:
            from_field = message['fields']['from']
            if from_field and '<' in from_field and '>' in from_field:
                email = from_field[from_field.find('<')+1:from_field.find('>')]
                name = from_field[:from_field.find('<')].strip()
                
                if email not in newsletters:
                    newsletters[email] = {
                        'name': name,
                        'count': 0,
                        'example_message_id': message['id']
                    }
                newsletters[email]['count'] += 1
                
        sorted_newsletters = dict(sorted(
            newsletters.items(), 
            key=lambda x: x[1]['count'], 
            reverse=True
        ))
        return sorted_newsletters

    def unsubscribe_from_newsletter(self, message_id):
        """Отписывается от рассылки по ID сообщения"""
        try:
            message = self.service.users().messages().get(
                userId=self.user_id,
                id=message_id,
                format='full'
            ).execute()
            
            headers = message['payload']['headers']
            unsubscribe_header = next(
                (header['value'] for header in headers 
                 if header['name'].lower() == 'list-unsubscribe'),
                None
            )
            
            if unsubscribe_header:
                if '<http' in unsubscribe_header:
                    urls = []
                    start = 0
                    while True:
                        start = unsubscribe_header.find('<http', start)
                        if start == -1:
                            break
                        end = unsubscribe_header.find('>', start)
                        if end == -1:
                            break
                        url = unsubscribe_header[start+1:end]
                        urls.append(url)
                        start = end + 1
                    
                    if urls:
                        print(f"\nДоступные ссылки для отписки:")
                        for i, url in enumerate(urls, 1):
                            print(f"{i}. {url}")
                        return True
                        
                elif '<mailto:' in unsubscribe_header:
                    print("\nДля этой рассылки доступна только отписка по email.")
                    print("К сожалению, для этого требуются дополнительные разрешения Gmail API.")
                    return False
                    
            print("\nНе найдены инструкции для отписки")
            return False
            
        except Exception as e:
            print(f"\nОшибка при получении информации об отписке: {str(e)}")
            return False

    def unsubscribe_all(self):
        """Получает ссылки для отписки от всех рассылок"""
        newsletters = self.get_newsletters()
        results = {
            'success': 0,
            'failed': 0,
            'urls': []
        }
        
        progress = IncrementalBar(
            f"{helpers.loader_icn} Поиск ссылок для отписки ".ljust(_progressPadding, " "),
            max=len(newsletters)
        )
        
        for email, info in newsletters.items():
            print(f"\n\nОбработка рассылки от: {info['name']} ({email})")
            if self.unsubscribe_from_newsletter(info['example_message_id']):
                results['success'] += 1
            else:
                results['failed'] += 1
            progress.next()
            
        progress.finish()
        
        print("\n=== Итоги ===")
        print(f"Найдены ссылки для отписки: {results['success']}")
        print(f"Не найдены способы отписки: {results['failed']}")
        return results
